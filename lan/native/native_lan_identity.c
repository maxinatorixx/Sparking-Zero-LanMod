#include "native_lan_identity.h"
#include <string.h>

static int hex_id(const unsigned char *value,size_t size) {
    for(size_t i=0;i<size;i++)
        if(!((value[i]>='0' && value[i]<='9') ||
             (value[i]>='a' && value[i]<='f'))) return 0;
    return 1;
}
int szero_lan_identity_valid(const unsigned char *value,size_t size) {
    return value && size==38 && !memcmp(value,"szlan:",6) && hex_id(value+6,32);
}
static int text(const unsigned char *value,size_t size) {
    return size && size<=SZERO_SESSION_CODEC_TEXT &&
        !memchr(value,0,size) && value[size]==0;
}
static int owned(const SzeroSessionCodec *codec) {
    if(codec->data.profile!=2 || codec->data.has_properties ||
       codec->data.id.data!=codec->id || codec->data.id.size!=32 ||
       codec->id[32] || !hex_id(codec->id,32) ||
       codec->data.members!=codec->members || !codec->data.capacity ||
       codec->data.capacity>SZERO_MATERIALIZER_MAX_MEMBERS ||
       !codec->data.member_count || codec->data.member_count>codec->data.capacity ||
       codec->data.numeric_count>SZERO_SESSION_CODEC_NUMERIC ||
       codec->data.numeric!=(codec->data.numeric_count?codec->numeric:NULL) ||
       codec->data.has_stream!=codec->stream.present || codec->stream.present>1 ||
       codec->stream.size>SZERO_WIRE_MAX_STREAM ||
       codec->stream.read_cursor>codec->stream.size ||
       codec->stream.write_cursor>codec->stream.size ||
       (!codec->stream.present && (codec->stream.size ||
         codec->stream.read_cursor || codec->stream.write_cursor))) return 0;
    unsigned owners=0;
    for(size_t i=0;i<codec->data.member_count;i++) {
        const SzeroMemberData *member=codec->members+i;
        const SzeroSessionCodecMemberStorage *storage=codec->storage+i;
        if(member->id.data!=storage->id || member->id.size!=32 ||
           storage->id[32] || !hex_id(storage->id,32) ||
           member->address.data!=storage->address ||
           member->address.size!=storage->address_size ||
           !text(storage->address,storage->address_size) || member->owner>1 ||
           member->optional_present>1 || member->field_8b!=0) return 0;
        owners+=member->owner;
        for(size_t j=0;j<2;j++)
            if(member->identity[j].data!=storage->identity[j] ||
               member->identity[j].size!=storage->identity_size[j] ||
               !text(storage->identity[j],storage->identity_size[j])) return 0;
        if(!szero_lan_identity_valid(storage->identity[0],storage->identity_size[0])) return 0;
        if(i && (member->join_order<=codec->members[i-1].join_order ||
                 !memcmp(storage->id,codec->storage[i-1].id,32))) return 0;
        for(size_t j=0;j<i;j++)
            if(!memcmp(storage->identity[0],codec->storage[j].identity[0],38) ||
               !memcmp(storage->id,codec->storage[j].id,32)) return 0;
    }
    return owners==1;
}
int szero_lan_identity_project(SzeroSessionCodec *codec,
    const unsigned char *self_lan,size_t self_lan_size,
    const SzeroIdentityWire *native_self,int require_local) {
    if(!codec || !native_self || (require_local!=0 && require_local!=1) ||
       !szero_lan_identity_valid(self_lan,self_lan_size) || !owned(codec)) return 0;
    unsigned char identity[2][SZERO_SESSION_CODEC_TEXT+1];
    size_t sizes[2];
    for(size_t j=0;j<2;j++) {
        uint64_t n=native_self->value[j].size;
        if(!n || n>SZERO_SESSION_CODEC_TEXT ||
           memchr(native_self->value[j].bytes,0,(size_t)n)) return 0;
        sizes[j]=(size_t)n;
        memcpy(identity[j],native_self->value[j].bytes,(size_t)n);
        identity[j][n]=0;
    }
    if(sizes[0]>=6 && !memcmp(identity[0],"szlan:",6)) return 0;
    size_t local=SIZE_MAX,count=0;
    for(size_t i=0;i<codec->data.member_count;i++)
        if(!memcmp(codec->storage[i].identity[0],self_lan,38)) {local=i;count++;}
    if(count!=(size_t)require_local) return 0;
    /* Every check precedes the first write, including source snapshotting. */
    if(require_local) for(size_t j=0;j<2;j++) {
        unsigned char *destination=codec->storage[local].identity[j];
        memset(destination,0,SZERO_SESSION_CODEC_TEXT+1);
        memcpy(destination,identity[j],sizes[j]);
        codec->storage[local].identity_size[j]=sizes[j];
        codec->members[local].identity[j]=(SzeroText){destination,sizes[j]};
    }
    return 1;
}
