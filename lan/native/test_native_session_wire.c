/* Owned-memory source marshalling contracts. Never executes game code. */
#include "native_session_wire.h"
#include "session_materializer.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct { uintptr_t start; size_t size; } Region;
typedef struct { Region regions[8]; size_t count; unsigned reads; } Memory;
static int read_owned(uintptr_t source, void *out, size_t size, void *user) {
    Memory *memory = user;
    memory->reads++;
    for (size_t i = 0; i < memory->count; ++i) {
        Region r = memory->regions[i];
        if (source >= r.start && source - r.start <= r.size && size <= r.size - (source - r.start)) {
            memcpy(out, (const void *)source, size);
            return 1;
        }
    }
    return 0;
}
static void region(Memory *memory, const void *source, size_t size) {
    assert(memory->count < 8);
    memory->regions[memory->count++] = (Region){(uintptr_t)source, size};
}

static const uintptr_t base = UINT64_C(0x140000000);
static SzeroStreamWire expected;
static unsigned factory_calls;
static unsigned char retained[SZERO_WIRE_MAX_STREAM];
static SzeroNativeResult *SZERO_NATIVE_CALL factory(SzeroNativeResult *output,
    uintptr_t unused, SzeroNativeResult *input) {
    assert(!unused && input->tag == 2);
    factory_calls++;
    const SzeroNativeDescriptor *d = (const void *)input->payload[0];
    assert(d->properties.count == 0 && d->properties.chain == 0);
    assert(d->properties.buckets == (uintptr_t)&d->properties.inline_bucket);
    assert(!d->settings.stream_allocator && d->settings.stream);
    const SzeroBorrowedStream *stream = (const void *)d->settings.stream;
    assert(stream->vtable == base + SZERO_STREAM_VTABLE_RVA);
    assert(!stream->reserved && stream->kind == 1 && !stream->allocator);
    assert(stream->data == (uintptr_t)stream->bytes);
    assert(stream->size == expected.size && stream->capacity == expected.size);
    assert(stream->read_cursor == expected.read_cursor);
    assert(stream->write_cursor == expected.write_cursor);
    assert(!memcmp(stream->bytes, expected.bytes, (size_t)expected.size));
    memcpy(retained, stream->bytes, (size_t)stream->size);
    output->tag = 2;
    output->payload[0] = (uintptr_t)retained;
    output->payload[1] = (uintptr_t)&factory_calls;
    return output;
}

static void inline_text(SzeroNativeString *value,const char *text) {
    size_t size=strlen(text);assert(size<=30);memset(value,0,sizeof(*value));
    unsigned char *bytes=(unsigned char *)value;bytes[0]=(unsigned char)(size<<2);
    memcpy(bytes+1,text,size);
}
static void member_capture_contract(void) {
    SzeroNativeDescriptor descriptor={0};SzeroNativeMemberNode nodes[2]={0};
    uintptr_t sentinel=(uintptr_t)&descriptor.members;
    descriptor.members.next=&nodes[0];descriptor.members.previous=&nodes[1];
    descriptor.members.count=2;descriptor.member_count=2;
    nodes[0].previous=(SzeroNativeMemberNode *)sentinel;nodes[0].next=&nodes[1];
    nodes[1].previous=&nodes[0];nodes[1].next=(SzeroNativeMemberNode *)sentinel;
    for(unsigned i=0;i<2;i++) {
        inline_text(&nodes[i].value.identity[0],i?"remote-first":"own-first");
        inline_text(&nodes[i].value.identity[1],i?"remote-second":"own-second");
        inline_text(&nodes[i].value.address,"127.0.0.1:12345");
    }
    nodes[0].value.field_88=255;nodes[0].value.optional_present=1;
    nodes[0].value.optional_value=249;nodes[0].value.field_8b=1;nodes[0].value.owner=1;
    Memory memory={0};region(&memory,&descriptor,sizeof(descriptor));region(&memory,nodes,sizeof(nodes));
    SzeroIdentityWire identity={0};
    assert(!szero_capture_identity_pair((uintptr_t)nodes[0].value.identity,read_owned,&memory,&identity));
    SzeroMemberWire out={0};
    assert(!szero_capture_local_member((uintptr_t)&descriptor,&identity,read_owned,&memory,&out));
    assert(out.field_88==255 && out.optional_present==1 && out.optional_value==249 && out.field_8b==1 && out.owner==1);
    assert(out.address.size==15 && !memcmp(out.address.bytes,"127.0.0.1:12345",15));
    SzeroMemberWire unchanged=out;
    nodes[1].value.identity[0]=nodes[0].value.identity[0];
    nodes[1].value.identity[1]=nodes[0].value.identity[1];
    assert(szero_capture_local_member((uintptr_t)&descriptor,&identity,read_owned,&memory,&out)==SZERO_WIRE_INVALID);
    assert(!memcmp(&out,&unchanged,sizeof(out)));
    inline_text(&nodes[1].value.identity[0],"remote-first");
    inline_text(&nodes[1].value.identity[1],"remote-second");
    nodes[0].value.optional_present=2;
    assert(szero_capture_local_member((uintptr_t)&descriptor,&identity,read_owned,&memory,&out)==SZERO_WIRE_INVALID);
    nodes[0].value.optional_present=1;nodes[1].previous=(void *)1;
    assert(szero_capture_local_member((uintptr_t)&descriptor,&identity,read_owned,&memory,&out)==SZERO_WIRE_INVALID);
    nodes[1].previous=&nodes[0];nodes[1].next=&nodes[0];
    assert(szero_capture_local_member((uintptr_t)&descriptor,&identity,read_owned,&memory,&out)==SZERO_WIRE_INVALID);
    nodes[1].next=(void *)sentinel;descriptor.member_count=3;
    assert(szero_capture_local_member((uintptr_t)&descriptor,&identity,read_owned,&memory,&out)==SZERO_WIRE_INVALID);
    descriptor.member_count=2;nodes[0].next=(void *)1;
    assert(szero_capture_local_member((uintptr_t)&descriptor,&identity,read_owned,&memory,&out)!=SZERO_WIRE_OK);
    assert(!memcmp(&out,&unchanged,sizeof(out)));
}

static void vector_stream_contract(void) {
    /* Exact64-byte native object in an isolated allowed region: reading the
     * inline family's72-byte header here MUST fail, so this detects overreads. */
    struct {
        uintptr_t vtable,reserved;
        uint64_t rd,wr;
        uintptr_t data;
        uint64_t size,capacity;
        uintptr_t allocator;
    } vector={0};
    _Static_assert(sizeof(vector)==0x40,"Exact vector object");
    unsigned char bytes[32];for(size_t i=0;i<sizeof(bytes);i++) bytes[i]=(unsigned char)(i*7);
    vector.vtable=base+SZERO_VECTOR_STREAM_VTABLE_RVA;
    vector.data=(uintptr_t)bytes;vector.size=32;vector.capacity=64;vector.rd=3;vector.wr=29;
    vector.allocator=UINTPTR_MAX; /* Metadata, not part of transmitted data. */
    SzeroNativeSettings settings={0};settings.capacity=2;settings.stream=(uintptr_t)&vector;
    Memory memory={0};region(&memory,&vector,sizeof(vector));region(&memory,bytes,sizeof(bytes));
    region(&memory,&settings,sizeof(settings));
    SzeroSettingsWire output={0};SzeroStreamInfo info={0};
    unsigned char before[sizeof(vector)];memcpy(before,&vector,sizeof(vector));
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info));
    assert(info.layout==SZERO_STREAM_VECTOR && !info.refusal && info.vtable_rva==SZERO_VECTOR_STREAM_VTABLE_RVA);
    assert(output.stream.present && output.stream.size==32 && output.stream.read_cursor==3 && output.stream.write_cursor==29);
    assert(!memcmp(output.stream.bytes,bytes,32) && !memcmp(before,&vector,sizeof(vector)));
    SzeroBorrowedStream rebuilt={0};assert(!szero_borrow_stream(&output.stream,base,&rebuilt));
    assert(rebuilt.vtable==base+SZERO_STREAM_VTABLE_RVA && rebuilt.kind==1);
    assert(rebuilt.read_cursor==3 && rebuilt.write_cursor==29 && !memcmp(rebuilt.bytes,bytes,32));
    SzeroSettingsWire unchanged=output;
    vector.wr=33;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_UNSUPPORTED_STREAM);
    assert(info.refusal==SZERO_STREAM_REFUSAL_WRITE_CURSOR && info.write_cursor==33 && !memcmp(&output,&unchanged,sizeof(output)));
    vector.wr=29;vector.size=65;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_INVALID);
    assert(info.refusal==SZERO_STREAM_REFUSAL_LENGTH && !memcmp(&output,&unchanged,sizeof(output)));
    vector.size=32;vector.rd=33;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_INVALID);
    assert(info.refusal==SZERO_STREAM_REFUSAL_READ_CURSOR);
    vector.rd=3;vector.data=1;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_UNREADABLE);
    assert(info.refusal==SZERO_STREAM_REFUSAL_DATA && !memcmp(&output,&unchanged,sizeof(output)));
    vector.vtable++;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_UNSUPPORTED_STREAM);
    assert(info.layout==SZERO_STREAM_UNKNOWN && info.refusal==SZERO_STREAM_REFUSAL_VTABLE);
    vector.vtable=base+SZERO_VECTOR_STREAM_VTABLE_RVA;vector.data=0;vector.rd=vector.wr=vector.size=0;
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info));
    assert(output.stream.present && !output.stream.size);
}

static void embedded_stream_contract(void) {
    /* Exact observed Quickmatch vtable146d15840: payload is object+30, not
     * the word stored at+20 (size) or+28 (capacity). */
    typedef struct {
        uintptr_t vtable,reserved;
        uint64_t rd,wr,size,capacity;
        unsigned char bytes[32];
    } Embedded;
    Embedded embedded={0};
    _Static_assert(offsetof(Embedded,bytes)==0x30,"Embedded data offset");
    embedded.vtable=base+SZERO_EMBEDDED_STREAM_VTABLE_RVA;
    embedded.rd=3;embedded.wr=29;embedded.size=embedded.capacity=32;
    for(size_t i=0;i<32;i++) embedded.bytes[i]=(unsigned char)(i*7);
    SzeroNativeSettings settings={0};settings.capacity=2;settings.stream=(uintptr_t)&embedded;
    Memory memory={0};region(&memory,&settings,sizeof(settings));region(&memory,&embedded,sizeof(embedded));
    SzeroSettingsWire output={0};SzeroStreamInfo info={0};
    unsigned char before[sizeof(embedded)];memcpy(before,&embedded,sizeof(embedded));
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info));
    assert(info.layout==SZERO_STREAM_EMBEDDED && !info.refusal && info.vtable_rva==0x6d15840);
    assert(output.stream.size==32 && output.stream.read_cursor==3 && output.stream.write_cursor==29);
    assert(!memcmp(output.stream.bytes,embedded.bytes,32) && !memcmp(before,&embedded,sizeof(embedded)));
    SzeroBorrowedStream rebuilt={0};assert(!szero_borrow_stream(&output.stream,base,&rebuilt));
    assert(rebuilt.kind==1 && rebuilt.size==32 && rebuilt.read_cursor==3 && rebuilt.write_cursor==29);
    assert(!memcmp(rebuilt.bytes,embedded.bytes,32));
    SzeroSettingsWire unchanged=output;
    embedded.capacity=31;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_INVALID);
    assert(info.refusal==SZERO_STREAM_REFUSAL_LENGTH && !memcmp(&output,&unchanged,sizeof(output)));
    embedded.capacity=32;embedded.rd=33;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_INVALID);
    assert(info.refusal==SZERO_STREAM_REFUSAL_READ_CURSOR);
    embedded.rd=3;embedded.wr=33;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_UNSUPPORTED_STREAM);
    assert(info.refusal==SZERO_STREAM_REFUSAL_WRITE_CURSOR);
    embedded.wr=29;memory.regions[1].size=0x30;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_UNREADABLE);
    assert(info.refusal==SZERO_STREAM_REFUSAL_DATA && !memcmp(&output,&unchanged,sizeof(output)));
    embedded.rd=embedded.wr=embedded.size=0;
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info));
    assert(output.stream.present && !output.stream.size);
    embedded.vtable++;
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&output,&info)==SZERO_WIRE_UNSUPPORTED_STREAM);
    assert(info.layout==SZERO_STREAM_UNKNOWN && info.refusal==SZERO_STREAM_REFUSAL_VTABLE);
}

static void inline64_stream_contract(void) {
    /* Newly recovered146d15df0 is NOT the72-byte known inline object.
     * Separate64-byte readable prefix detects an accidental allocator read;
     * exact payload region checks that no slack or native ownership escapes. */
    typedef struct {
        uintptr_t vtable,reserved;
        uint64_t rd,wr;
        uint32_t kind,padding;
        uintptr_t data;
        uint64_t size,capacity;
        unsigned char bytes[64];
    } Inline64;
    _Static_assert(offsetof(Inline64,bytes)==0x40,"Inline64 data offset");
    Inline64 value={0};
    value.vtable=base+SZERO_INLINE64_STREAM_VTABLE_RVA;
    value.kind=1;value.data=(uintptr_t)value.bytes;
    value.rd=3;value.wr=29;value.size=32;value.capacity=64;
    for(size_t n=0;n<sizeof(value.bytes);n++) value.bytes[n]=(unsigned char)(n*11+7);
    unsigned char before[sizeof(value)];memcpy(before,&value,sizeof(value));
    SzeroNativeSettings settings={0};settings.capacity=2;settings.stream=(uintptr_t)&value;
    Memory memory={0};region(&memory,&settings,sizeof(settings));
    region(&memory,&value,0x40);region(&memory,value.bytes,32);
    struct {uint64_t left;SzeroSettingsWire output;uint64_t right;} guarded={0};
    guarded.left=UINT64_C(0x12345678abcdef01);guarded.right=UINT64_C(0xaabbccdd99887766);
    SzeroStreamInfo info={0};
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&guarded.output,&info));
    assert(info.layout==5 && info.layout==SZERO_STREAM_INLINE64 && !info.refusal);
    assert(info.kind==1 && info.vtable_rva==SZERO_INLINE64_STREAM_VTABLE_RVA);
    assert(guarded.output.stream.present && guarded.output.stream.size==32);
    assert(guarded.output.stream.read_cursor==3 && guarded.output.stream.write_cursor==29);
    assert(!memcmp(guarded.output.stream.bytes,value.bytes,32) && !memcmp(before,&value,sizeof(value)));
    SzeroBorrowedStream rebuilt={0};
    assert(!szero_borrow_stream(&guarded.output.stream,base,&rebuilt));
    assert(rebuilt.vtable==base+SZERO_STREAM_VTABLE_RVA && rebuilt.kind==1 && !rebuilt.allocator);
    assert(rebuilt.read_cursor==3 && rebuilt.write_cursor==29 && rebuilt.size==32);
    assert(!memcmp(rebuilt.bytes,value.bytes,32));
    SzeroSettingsWire unchanged=guarded.output;
#define INLINE64_REFUSE(code,reason) do { \
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&guarded.output,&info)==(code)); \
    assert(info.refusal==(reason) && !memcmp(&guarded.output,&unchanged,sizeof(unchanged))); \
    assert(guarded.left==UINT64_C(0x12345678abcdef01) && guarded.right==UINT64_C(0xaabbccdd99887766)); \
} while(0)
    value.kind=2;INLINE64_REFUSE(SZERO_WIRE_UNSUPPORTED_STREAM,SZERO_STREAM_REFUSAL_KIND);
    value.kind=1;value.capacity=31;INLINE64_REFUSE(SZERO_WIRE_INVALID,SZERO_STREAM_REFUSAL_LENGTH);
    value.capacity=64;value.rd=33;INLINE64_REFUSE(SZERO_WIRE_INVALID,SZERO_STREAM_REFUSAL_READ_CURSOR);
    value.rd=3;value.wr=33;INLINE64_REFUSE(SZERO_WIRE_UNSUPPORTED_STREAM,SZERO_STREAM_REFUSAL_WRITE_CURSOR);
    value.wr=29;value.data=1;INLINE64_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_DATA);
    value.data=UINTPTR_MAX-7;INLINE64_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_DATA);
    value.data=(uintptr_t)value.bytes;memory.regions[2].size=31;
    INLINE64_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_DATA);
    memory.regions[2].size=32;memory.regions[1].size=0x3f;
    INLINE64_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_HEADER);
    memory.regions[1].size=0x40;value.vtable++;
    INLINE64_REFUSE(SZERO_WIRE_UNSUPPORTED_STREAM,SZERO_STREAM_REFUSAL_VTABLE);
    assert(info.layout==SZERO_STREAM_UNKNOWN);
    value.vtable=base+SZERO_INLINE64_STREAM_VTABLE_RVA;
    value.size=SZERO_WIRE_MAX_STREAM+1;value.capacity=value.size;
    INLINE64_REFUSE(SZERO_WIRE_INVALID,SZERO_STREAM_REFUSAL_LENGTH);
    value.size=value.rd=value.wr=0;value.capacity=64;
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&guarded.output,&info));
    assert(guarded.output.stream.present && !guarded.output.stream.size && info.layout==SZERO_STREAM_INLINE64);
    assert(guarded.left==UINT64_C(0x12345678abcdef01) && guarded.right==UINT64_C(0xaabbccdd99887766));
#undef INLINE64_REFUSE
}

static void view_stream_contract(void) {
    struct {uintptr_t vt,reserved;uint64_t rd,size;uintptr_t data;} view={0};
    _Static_assert(sizeof(view)==0x28,"Exact borrowed view, no allocator word");
    unsigned char payload[32];for(unsigned i=0;i<32;i++) payload[i]=(unsigned char)(i*9);
    view.vt=base+SZERO_VIEW_STREAM_VTABLE_RVA;view.rd=3;view.size=32;view.data=(uintptr_t)payload;
    unsigned char before[sizeof(view)];memcpy(before,&view,sizeof(view));
    SzeroNativeSettings settings={0};settings.capacity=2;settings.stream=(uintptr_t)&view;
    Memory memory={0};region(&memory,&settings,sizeof(settings));
    region(&memory,&view,sizeof(view));region(&memory,payload,sizeof(payload));
    struct {uint64_t left;SzeroSettingsWire out;uint64_t right;} guarded={0};
    guarded.left=111;guarded.right=222;SzeroStreamInfo info={0};
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&guarded.out,&info));
    assert(info.layout==SZERO_STREAM_VIEW && !info.refusal && !info.kind);
    assert(guarded.out.stream.present && guarded.out.stream.size==32);
    assert(guarded.out.stream.read_cursor==3 && !guarded.out.stream.write_cursor);
    assert(!memcmp(guarded.out.stream.bytes,payload,32) && !memcmp(before,&view,sizeof(view)));
    SzeroBorrowedStream rebuilt={0};
    assert(!szero_borrow_stream(&guarded.out.stream,base,&rebuilt));
    assert(rebuilt.size==32 && rebuilt.read_cursor==3 && !rebuilt.write_cursor);
    assert(!memcmp(rebuilt.bytes,payload,32));
    SzeroSettingsWire unchanged=guarded.out;
#define VIEW_REFUSE(code,reason) do { \
    assert(szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&guarded.out,&info)==(code)); \
    assert(info.refusal==(reason) && !memcmp(&guarded.out,&unchanged,sizeof(unchanged))); \
    assert(guarded.left==111 && guarded.right==222); \
} while(0)
    view.rd=33;VIEW_REFUSE(SZERO_WIRE_INVALID,SZERO_STREAM_REFUSAL_READ_CURSOR);
    view.rd=3;view.size=SZERO_WIRE_MAX_STREAM+1;VIEW_REFUSE(SZERO_WIRE_INVALID,SZERO_STREAM_REFUSAL_LENGTH);
    view.size=32;view.data=1;VIEW_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_DATA);
    view.data=UINTPTR_MAX-7;VIEW_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_DATA);
    view.data=(uintptr_t)payload;memory.regions[2].size=31;
    VIEW_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_DATA);
    memory.regions[2].size=32;memory.regions[1].size=39;
    VIEW_REFUSE(SZERO_WIRE_UNREADABLE,SZERO_STREAM_REFUSAL_HEADER);
    memory.regions[1].size=40;view.vt++;
    VIEW_REFUSE(SZERO_WIRE_UNSUPPORTED_STREAM,SZERO_STREAM_REFUSAL_VTABLE);
    view.vt=base+SZERO_VIEW_STREAM_VTABLE_RVA;view.rd=view.size=view.data=0;
    assert(!szero_capture_settings_info((uintptr_t)&settings,base,read_owned,&memory,&guarded.out,&info));
    assert(guarded.out.stream.present && !guarded.out.stream.size && info.layout==SZERO_STREAM_VIEW);
    view.rd=1;unchanged=guarded.out;VIEW_REFUSE(SZERO_WIRE_INVALID,SZERO_STREAM_REFUSAL_READ_CURSOR);
#undef VIEW_REFUSE
}

int main(void) {
    view_stream_contract();
    vector_stream_contract();
    embedded_stream_contract();
    inline64_stream_contract();
    int32_t numbers[3] = {INT32_MIN, 9, INT32_MAX};
    SzeroNativeSettings native = {0};
    native.compatibility = UINT32_MAX;
    native.numeric = (uintptr_t)numbers;
    native.numeric_count = native.numeric_capacity = 3;
    native.capacity = 2;
    Memory memory = {0};
    region(&memory, &native, sizeof(native));
    region(&memory, numbers, sizeof(numbers));
    SzeroSettingsWire wire;
    memset(&wire, 0xa5, sizeof(wire));
    assert(szero_capture_settings((uintptr_t)&native, base, read_owned, &memory, &wire) == 0);
    assert(wire.compatibility == UINT32_MAX && wire.numeric_count == 3 && wire.capacity == 2);
    assert(!wire.stream.present && !memcmp(wire.numeric, numbers, sizeof(numbers)));

    SzeroBorrowedStream stream = {0};
    stream.vtable = base + SZERO_STREAM_VTABLE_RVA;
    stream.kind = 1;
    stream.data = (uintptr_t)stream.bytes;
    stream.size = 128;
    stream.capacity = 256;
    stream.read_cursor = 3;
    stream.write_cursor = 121;
    for (size_t i = 0; i < 128; ++i) stream.bytes[i] = (unsigned char)(i * 13);
    region(&memory, &stream, sizeof(stream));
    native.stream = (uintptr_t)&stream;
    assert(szero_capture_settings((uintptr_t)&native, base, read_owned, &memory, &wire) == 0);
    expected = wire.stream;
    assert(wire.stream.present && wire.stream.size == 128 && wire.stream.read_cursor == 3 &&
        wire.stream.write_cursor == 121 && !memcmp(wire.stream.bytes, stream.bytes, 128));
    SzeroBorrowedStream rebuilt;
    assert(szero_borrow_stream(&wire.stream, base, &rebuilt) == 0);
    assert(rebuilt.data == (uintptr_t)rebuilt.bytes && rebuilt.vtable == stream.vtable);
    assert(rebuilt.size == 128 && rebuilt.capacity == 128 && !rebuilt.allocator);
    assert(!memcmp(rebuilt.bytes, stream.bytes, 128));

    SzeroSettingsWire unchanged = wire;
#define BAD_CAPTURE(code) do { \
    assert(szero_capture_settings((uintptr_t)&native, base, read_owned, &memory, &wire) == (code)); \
    assert(!memcmp(&wire, &unchanged, sizeof(wire))); \
} while (0)
    stream.vtable++;
    BAD_CAPTURE(SZERO_WIRE_UNSUPPORTED_STREAM);
    stream.vtable--;
    stream.kind = 2;
    BAD_CAPTURE(SZERO_WIRE_UNSUPPORTED_STREAM);
    stream.kind = 1;
    stream.size = SZERO_WIRE_MAX_STREAM + 1;
    BAD_CAPTURE(SZERO_WIRE_INVALID);
    stream.size = 128;
    stream.capacity = 127;
    BAD_CAPTURE(SZERO_WIRE_INVALID);
    stream.capacity = 256;
    stream.read_cursor = 129;
    BAD_CAPTURE(SZERO_WIRE_INVALID);
    stream.read_cursor = 3;
    stream.write_cursor = 129;
    BAD_CAPTURE(SZERO_WIRE_UNSUPPORTED_STREAM);
    stream.write_cursor = 121;
    stream.data = UINTPTR_MAX - 2;
    BAD_CAPTURE(SZERO_WIRE_UNREADABLE);
    stream.data = (uintptr_t)stream.bytes;
    native.numeric_count = 33;
    BAD_CAPTURE(SZERO_WIRE_INVALID);
    native.numeric_count = 4;
    BAD_CAPTURE(SZERO_WIRE_INVALID);
    native.numeric_count = 3;
    native.numeric = 1;
    BAD_CAPTURE(SZERO_WIRE_UNREADABLE);
    native.numeric = (uintptr_t)numbers;
    assert(szero_capture_settings(UINTPTR_MAX - 2, base, read_owned, &memory, &wire) == SZERO_WIRE_UNREADABLE);
    assert(szero_capture_settings((uintptr_t)&native, UINTPTR_MAX, read_owned, &memory, &wire) == SZERO_WIRE_INVALID);

    /* Known native identity pair captured exactly, including heap-form data;
     * no semantic labels, account lookup or raw diagnostic output. */
    unsigned char identity[64] = {0};
    identity[0] = 4 * 5;
    memcpy(identity + 1, "local", 5);
    unsigned char second[64];
    memset(second, 'b', sizeof(second));
    uint64_t long_string[4] = {1, (uintptr_t)second, sizeof(second), sizeof(second)};
    memcpy(identity + 32, long_string, sizeof(long_string));
    region(&memory, identity, sizeof(identity));
    region(&memory, second, sizeof(second));
    SzeroIdentityWire pair = {0};
    assert(!szero_capture_identity_pair((uintptr_t)identity, read_owned, &memory, &pair));
    assert(pair.value[0].size == 5 && !memcmp(pair.value[0].bytes, "local", 5));
    assert(pair.value[1].size == 64 && !memcmp(pair.value[1].bytes, second, 64));
    second[10] = 0;
    assert(szero_capture_identity_pair((uintptr_t)identity, read_owned, &memory, &pair) == SZERO_WIRE_INVALID);
    assert(pair.value[1].bytes[10] == 'b');
    second[10] = 'b';
    long_string[2] = 256;
    memcpy(identity + 32, long_string, sizeof(long_string));
    assert(szero_capture_identity_pair((uintptr_t)identity, read_owned, &memory, &pair) == SZERO_WIRE_INVALID);

    SzeroMemberData member = {0};
    member.id = (SzeroText){(const unsigned char *)"id", 2};
    member.identity[0] = member.identity[1] = member.id;
    member.address = (SzeroText){(const unsigned char *)"127.0.0.1:1", 11};
    member.owner = 1;
    SzeroSessionData data = {0};
    data.profile = 2;
    data.id = member.id;
    data.compatibility = native.compatibility;
    data.numeric = numbers;
    data.numeric_count = 3;
    data.members = &member;
    data.member_count = 1;
    data.capacity = 2;
    data.has_stream = 1;
    SzeroNativeResult result = {0};
    assert(!szero_materialize_session_stream(&data, &expected, base, factory, &result));
    assert(factory_calls == 1 && !memcmp(retained, expected.bytes, (size_t)expected.size));
    assert(szero_materialize_session_stream(&data, &expected, base, factory, &result) == SZERO_MATERIALIZE_INVALID);
    memset(&result, 0, sizeof(result));
    data.has_properties = 1;
    assert(szero_materialize_session_stream(&data, &expected, base, factory, &result) == SZERO_MATERIALIZE_UNSUPPORTED);
    data.has_properties = 0;
    data.has_stream = 0;
    assert(szero_materialize_session_stream(&data, &expected, base, factory, &result) == SZERO_MATERIALIZE_INVALID);
    data.has_stream = 1;
    assert(szero_materialize_session_stream(&data, &expected, 0, factory, &result) == SZERO_MATERIALIZE_INVALID);
    assert(szero_materialize_session(&data, factory, &result) == SZERO_MATERIALIZE_UNSUPPORTED);
    assert(factory_calls == 1);
    member_capture_contract();
    puts("native session wire contracts passed (owned synthetic memory only)");
    return 0;
}
