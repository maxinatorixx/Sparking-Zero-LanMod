#include "native_session_wire.h"
#include <string.h>
#include <stdlib.h>

_Static_assert(sizeof(uintptr_t) == 8, "Exact x64 layout only");
_Static_assert(offsetof(SzeroBorrowedStream, read_cursor) == 0x10, "Read cursor");
_Static_assert(offsetof(SzeroBorrowedStream, write_cursor) == 0x18, "Write cursor");
_Static_assert(offsetof(SzeroBorrowedStream, kind) == 0x20, "Stream kind");
_Static_assert(offsetof(SzeroBorrowedStream, data) == 0x28, "Stream data");
_Static_assert(offsetof(SzeroBorrowedStream, size) == 0x30, "Stream size");
_Static_assert(offsetof(SzeroBorrowedStream, allocator) == 0x40, "Allocator");
_Static_assert(offsetof(SzeroBorrowedStream, bytes) == 0x48, "Inline bytes");

typedef struct {
    uint32_t compatibility, padding;
    uintptr_t numeric;
    uint64_t count, capacity;
    uintptr_t allocator, stream_allocator, stream;
    uint8_t member_capacity, tail[7];
} Settings;
_Static_assert(sizeof(Settings) == 0x40, "Settings layout");

/* Validate the full range before delegating; do not wrap addresses into a
 * different mapped region, even when a fixture reader might accept it. */
static int read_range(SzeroWireRead read, void *user, uintptr_t source,
    void *output, size_t size) {
    return source && size <= UINTPTR_MAX - source && read(source, output, size, user);
}

static int capture_text(uintptr_t source, SzeroWireRead read,void *user,SzeroTextWire *output) {
        SzeroTextWire result={0};
        uint64_t string[4];
        if (!read_range(read, user, source, string, sizeof(string)))
            return SZERO_WIRE_UNREADABLE;
        size_t size;
        if (string[0] & 1) {
            if (string[2] > SZERO_WIRE_MAX_TEXT || string[2] > string[3])
                return SZERO_WIRE_INVALID;
            size = (size_t)string[2];
            if (size && !read_range(read, user, (uintptr_t)string[1], result.bytes,
                size)) return SZERO_WIRE_UNREADABLE;
        } else {
            size = ((const unsigned char *)string)[0] >> 2;
            if (size > 30) return SZERO_WIRE_INVALID;
            if (size) memcpy(result.bytes, (unsigned char *)string + 1, size);
        }
        if (size && memchr(result.bytes, 0, size)) return SZERO_WIRE_INVALID;
        result.size = size;
        *output=result;
        return SZERO_WIRE_OK;
}
int szero_capture_identity_pair(uintptr_t source, SzeroWireRead read,
    void *user, SzeroIdentityWire *output) {
    if (!read || !output || source > UINTPTR_MAX - 0x40) return SZERO_WIRE_INVALID;
    SzeroIdentityWire result = {0};
    for (size_t i = 0; i < 2; ++i) {
        int rc=capture_text(source+i*0x20,read,user,&result.value[i]);
        if(rc) return rc;
    }
    *output = result;
    return SZERO_WIRE_OK;
}

int szero_capture_local_member(uintptr_t descriptor,const SzeroIdentityWire *identity,
    SzeroWireRead read,void *user,SzeroMemberWire *output) {
    if(!read || !output || !identity || !descriptor || descriptor>UINTPTR_MAX-0xe8)
        return SZERO_WIRE_INVALID;
    for(size_t i=0;i<2;i++)
        if(!identity->value[i].size || identity->value[i].size>SZERO_WIRE_MAX_TEXT)
            return SZERO_WIRE_INVALID;
    uintptr_t links[3];uint8_t count=0;
    if(!read_range(read,user,descriptor+0xc8,links,sizeof(links)) ||
       !read_range(read,user,descriptor+0xe0,&count,1)) return SZERO_WIRE_UNREADABLE;
    if(!count || count>8 || links[2]!=count) return SZERO_WIRE_INVALID;
    uintptr_t sentinel=descriptor+0xc8,node=links[0],previous=sentinel;
    SzeroMemberWire result={0};unsigned found=0;
    for(unsigned index=0;index<count;index++) {
        uintptr_t next[2];SzeroMemberWire member={0};
        if(!node || node==sentinel || node>UINTPTR_MAX-0xa0 || (node&7)) return SZERO_WIRE_INVALID;
        if(!read_range(read,user,node,next,sizeof(next))) return SZERO_WIRE_UNREADABLE;
        if(next[1]!=previous) return SZERO_WIRE_INVALID;
        int rc=szero_capture_identity_pair(node+0x38,read,user,&member.identity);
        if(rc) return rc;
        rc=capture_text(node+0x78,read,user,&member.address);
        if(rc) return rc;
        uint8_t flags[5];
        if(!read_range(read,user,node+0x98,flags,sizeof(flags))) return SZERO_WIRE_UNREADABLE;
        if(flags[1]>1 || flags[3]>1 || flags[4]>1) return SZERO_WIRE_INVALID;
        int same=1;
        for(size_t i=0;i<2;i++)
            if(identity->value[i].size!=member.identity.value[i].size ||
               memcmp(identity->value[i].bytes,member.identity.value[i].bytes,
                      (size_t)identity->value[i].size)) same=0;
        if(same) {
            if(found++) return SZERO_WIRE_INVALID;
            member.field_88=flags[0];member.optional_present=flags[1];
            member.optional_value=flags[2];member.field_8b=flags[3];member.owner=flags[4];
            result=member;
        }
        previous=node;node=next[0];
    }
    if(node!=sentinel || previous!=links[1] || found!=1) return SZERO_WIRE_INVALID;
    *output=result;
    return SZERO_WIRE_OK;
}

int szero_validate_stream(const SzeroStreamWire *stream) {
    if (!stream || stream->present > 1 || stream->size > SZERO_WIRE_MAX_STREAM ||
        stream->read_cursor > stream->size)
        return SZERO_WIRE_INVALID;
    if (!stream->present && (stream->size || stream->read_cursor || stream->write_cursor))
        return SZERO_WIRE_INVALID;
    /* Native write-cursor restoration can grow a stream beyond its captured
     * byte length. This profile intentionally does not synthesize that extra
     * storage/content; this is unsupported, not proof of corrupt native data. */
    if (stream->write_cursor > stream->size) return SZERO_WIRE_UNSUPPORTED_STREAM;
    return SZERO_WIRE_OK;
}

static int capture_settings(uintptr_t source, uintptr_t image_base,
    SzeroWireRead read, void *user, SzeroSettingsWire *output,SzeroStreamInfo *info) {
    if (!read || !output || !image_base ||
        image_base > UINTPTR_MAX - SZERO_STREAM_VTABLE_RVA)
        return SZERO_WIRE_INVALID;
    Settings settings;
    if (!read_range(read, user, source, &settings, sizeof(settings)))
        return SZERO_WIRE_UNREADABLE;
    if (settings.count > SZERO_WIRE_MAX_NUMERIC || settings.count > settings.capacity ||
        (!settings.stream && settings.stream_allocator)) return SZERO_WIRE_INVALID;
    output->compatibility = settings.compatibility;
    output->numeric_count = settings.count;
    output->capacity = settings.member_capacity;
    if (settings.count && !read_range(read, user, settings.numeric, output->numeric,
        (size_t)settings.count * sizeof(int32_t))) return SZERO_WIRE_UNREADABLE;
    if (settings.stream) {
        uintptr_t vtable=0,data=0;uint64_t size=0,capacity=0,rd=0,wr=0;
        info->layout=SZERO_STREAM_UNKNOWN;info->refusal=SZERO_STREAM_REFUSAL_HEADER;
        if(!read_range(read,user,settings.stream,&vtable,8)) return SZERO_WIRE_UNREADABLE;
        /* A module-relative offset is evidence for a future exact-build static
         * inspection, never an absolute runtime address. */
        if(vtable>=image_base && vtable-image_base<0x9000000)
            info->vtable_rva=(uint32_t)(vtable-image_base);
        /* Inline family:72B prefix followed by inline payload. */
        struct {
            uintptr_t vtable, reserved;
            uint64_t read_cursor, write_cursor;
            uint32_t kind, padding;
            uintptr_t data;
            uint64_t size, capacity;
            uintptr_t allocator;
        } header;
        _Static_assert(sizeof(header)==offsetof(SzeroBorrowedStream,bytes), "Header prefix");
        if(vtable==image_base+SZERO_STREAM_VTABLE_RVA) {
            info->layout=SZERO_STREAM_INLINE;
            if(!read_range(read,user,settings.stream,&header,sizeof(header))) return SZERO_WIRE_UNREADABLE;
            info->kind=header.kind;
            if(header.kind!=1) {info->refusal=SZERO_STREAM_REFUSAL_KIND;return SZERO_WIRE_UNSUPPORTED_STREAM;}
            data=header.data;size=header.size;capacity=header.capacity;
            rd=header.read_cursor;wr=header.write_cursor;
        } else if(vtable==image_base+SZERO_VECTOR_STREAM_VTABLE_RVA) {
            /*145839ac0 allocates EXACTLY64B: vector at+20, not a kind word.
             * +90 size getter reads+28; +280 data getter reads+20. */
            struct {
                uintptr_t vtable,reserved;
                uint64_t read_cursor,write_cursor;
                uintptr_t data;
                uint64_t size,capacity;
                uintptr_t allocator;
            } vector;
            _Static_assert(sizeof(vector)==0x40,"Vector stream header");
            info->layout=SZERO_STREAM_VECTOR;
            if(!read_range(read,user,settings.stream,&vector,sizeof(vector))) return SZERO_WIRE_UNREADABLE;
            data=vector.data;size=vector.size;capacity=vector.capacity;
            rd=vector.read_cursor;wr=vector.write_cursor;
        } else if(vtable==image_base+SZERO_EMBEDDED_STREAM_VTABLE_RVA) {
            /* Actual Quickmatch vtable from runtime.145839350 sets size+20,
             * capacity+28 and copies bytes into object+30. This family has
             * neither a kind field nor an external data pointer. */
            struct {
                uintptr_t vtable,reserved;
                uint64_t read_cursor,write_cursor,size,capacity;
            } embedded;
            _Static_assert(sizeof(embedded)==0x30,"Embedded stream header");
            info->layout=SZERO_STREAM_EMBEDDED;
            if(!read_range(read,user,settings.stream,&embedded,sizeof(embedded))) return SZERO_WIRE_UNREADABLE;
            data=settings.stream+sizeof(embedded);size=embedded.size;capacity=embedded.capacity;
            rd=embedded.read_cursor;wr=embedded.write_cursor;
        } else if(vtable==image_base+SZERO_INLINE64_STREAM_VTABLE_RVA) {
            /* 145a928c0 / 14228cfb0 / 14593c5a0 construct the separate
             * allocator-less inline family. Its bytes start at+40, NOT+48;
             * +2b0 is the zero-return leaf1410fdc80. Read only its64B prefix.
             * This borrows bytes; never call its getter/destructor. */
            struct {
                uintptr_t vtable,reserved;
                uint64_t read_cursor,write_cursor;
                uint32_t kind,padding;
                uintptr_t data;
                uint64_t size,capacity;
            } inline64;
            _Static_assert(sizeof(inline64)==0x40,"Allocator-less inline header");
            info->layout=SZERO_STREAM_INLINE64;
            if(!read_range(read,user,settings.stream,&inline64,sizeof(inline64))) return SZERO_WIRE_UNREADABLE;
            info->kind=inline64.kind;
            if(inline64.kind!=1) {info->refusal=SZERO_STREAM_REFUSAL_KIND;return SZERO_WIRE_UNSUPPORTED_STREAM;}
            data=inline64.data;size=inline64.size;capacity=inline64.capacity;
            rd=inline64.read_cursor;wr=inline64.write_cursor;
        } else if(vtable==image_base+SZERO_VIEW_STREAM_VTABLE_RVA) {
            /*145923a50 allocates EXACTLY40B;1429146a0 constructs a nonempty
             * borrowed view: rd+10,size+18,data+20. Original getters +80 read
             * +10,+88 returns0,+90/+98 read+18,+280 reads+20. No allocator,
             * kind or writable capacity field; never call native methods. */
            struct {
                uintptr_t vtable,reserved;
                uint64_t read_cursor,size;
                uintptr_t data;
            } view;
            _Static_assert(sizeof(view)==0x28,"Read-only view stream header");
            info->layout=SZERO_STREAM_VIEW;
            if(!read_range(read,user,settings.stream,&view,sizeof(view))) return SZERO_WIRE_UNREADABLE;
            data=view.data;size=capacity=view.size;rd=view.read_cursor;wr=0;
        } else {
            info->refusal=SZERO_STREAM_REFUSAL_VTABLE;
            return SZERO_WIRE_UNSUPPORTED_STREAM;
        }
        info->size=size;info->read_cursor=rd;info->write_cursor=wr;
        output->stream.present = 1;
        output->stream.size = size;
        output->stream.read_cursor = rd;
        output->stream.write_cursor = wr;
        info->refusal=SZERO_STREAM_REFUSAL_LENGTH;
        if(size>capacity || size>SZERO_WIRE_MAX_STREAM) return SZERO_WIRE_INVALID;
        if(rd>size) {info->refusal=SZERO_STREAM_REFUSAL_READ_CURSOR;return SZERO_WIRE_INVALID;}
        if(wr>size) {info->refusal=SZERO_STREAM_REFUSAL_WRITE_CURSOR;return SZERO_WIRE_UNSUPPORTED_STREAM;}
        int validation = szero_validate_stream(&output->stream);
        if (validation) return validation;
        info->refusal=SZERO_STREAM_REFUSAL_DATA;
        if(size && !read_range(read,user,data,output->stream.bytes,(size_t)size)) return SZERO_WIRE_UNREADABLE;
        info->refusal=SZERO_STREAM_REFUSAL_NONE;
    }
    return SZERO_WIRE_OK;
}

int szero_capture_settings(uintptr_t source, uintptr_t image_base,
    SzeroWireRead read, void *user, SzeroSettingsWire *output) {
    return szero_capture_settings_info(source,image_base,read,user,output,NULL);
}
int szero_capture_settings_info(uintptr_t source, uintptr_t image_base,
    SzeroWireRead read, void *user, SzeroSettingsWire *output,SzeroStreamInfo *info) {
    SzeroStreamInfo details={0};
    if(info) *info=details;
    if(!output) return SZERO_WIRE_INVALID;
    /* Keep transactional output semantics without a large native-fiber local.
     * This storage is ours, never passed to a native destructor. */
    SzeroSettingsWire *captured=calloc(1,sizeof(*captured));
    if(!captured) return SZERO_WIRE_INVALID;
    int rc=capture_settings(source,image_base,read,user,captured,&details);
    if(rc==SZERO_WIRE_OK) memcpy(output,captured,sizeof(*output));
    if(info) *info=details;
    free(captured);
    return rc;
}

int szero_borrow_stream(const SzeroStreamWire *stream, uintptr_t image_base,
    SzeroBorrowedStream *output) {
    if (!output || !image_base || image_base > UINTPTR_MAX - SZERO_STREAM_VTABLE_RVA)
        return SZERO_WIRE_INVALID;
    int validation = szero_validate_stream(stream);
    if (validation) return validation;
    memset(output, 0, sizeof(*output));
    if (!stream->present) return SZERO_WIRE_OK;
    output->vtable = image_base + SZERO_STREAM_VTABLE_RVA;
    output->read_cursor = stream->read_cursor;
    output->write_cursor = stream->write_cursor;
    output->kind = 1;
    output->data = (uintptr_t)output->bytes;
    output->size = output->capacity = stream->size;
    if (stream->size) memcpy(output->bytes, stream->bytes, (size_t)stream->size);
    return SZERO_WIRE_OK;
}
