#include "native_lan_identity.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static const unsigned char lan_a[]="szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static const unsigned char lan_b[]="szlan:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
static void initialize(SzeroSessionCodec *codec,size_t count) {
    memset(codec,0,sizeof(*codec));
    codec->data.profile=2;codec->data.capacity=count>2?8:2;
    memset(codec->id,'c',32);codec->data.id=(SzeroText){codec->id,32};
    codec->data.member_count=count;codec->data.members=codec->members;
    for(size_t i=0;i<count;i++) {
        SzeroSessionCodecMemberStorage *s=codec->storage+i;
        SzeroMemberData *m=codec->members+i;
        memset(s->id,"def12345"[i],32);m->id=(SzeroText){s->id,32};
        m->join_order=i;m->owner=i==0;
        static const char digits[]="abcdef12";
        memcpy(s->identity[0],"szlan:",6);memset(s->identity[0]+6,digits[i],32);s->identity_size[0]=38;
        memcpy(s->identity[1],"persona",8);s->identity_size[1]=7;
        memcpy(s->address,"127.0.0.1:4000",15);s->address_size=14;
        m->address=(SzeroText){s->address,14};
        for(size_t j=0;j<2;j++) m->identity[j]=(SzeroText){s->identity[j],s->identity_size[j]};
    }
}
static SzeroIdentityWire native_self;
static void rejected(SzeroSessionCodec *codec,const unsigned char *self,size_t size,
    int require) {
    SzeroSessionCodec before=*codec;
    assert(!szero_lan_identity_project(codec,self,size,&native_self,require));
    assert(!memcmp(codec,&before,sizeof(before)));
}
int main(void) {
    native_self.value[0].size=17;memcpy(native_self.value[0].bytes,"76561198000000000",17);
    native_self.value[1].size=7;memcpy(native_self.value[1].bytes,"persona",7);
    SzeroIdentityWire before=native_self;
    SzeroSessionCodec a,b;
    initialize(&a,2);initialize(&b,2);
    assert(szero_lan_identity_valid(lan_a,38));
    assert(!szero_lan_identity_valid(lan_a,SIZE_MAX));
    assert(!szero_lan_identity_valid(NULL,38));
    assert(szero_lan_identity_project(&a,lan_a,38,&native_self,1));
    assert(szero_lan_identity_project(&b,lan_b,38,&native_self,1));
    /* Same actual account and persona, but isolated temporary local views. */
    assert(a.members[0].identity[0].size==17 && b.members[1].identity[0].size==17);
    assert(!memcmp(a.members[0].identity[0].data,b.members[1].identity[0].data,17));
    assert(szero_lan_identity_valid(a.members[1].identity[0].data,38));
    assert(szero_lan_identity_valid(b.members[0].identity[0].data,38));
    assert(a.members[0].owner==1 && a.members[1].owner==0);
    assert(b.members[0].owner==1 && b.members[1].owner==0);
    assert(!memcmp(&before,&native_self,sizeof(before)));
    rejected(&a,lan_a,38,1); /* Reprojection is forbidden. */
    initialize(&a,1);
    SzeroSessionCodec unchanged=a;
    assert(szero_lan_identity_project(&a,lan_b,38,&native_self,0));
    assert(!memcmp(&a,&unchanged,sizeof(a))); /* Remote-only search view. */
    rejected(&a,lan_a,38,0);rejected(&a,lan_b,38,1);
    rejected(&a,lan_a,37,1);rejected(&a,lan_a,SIZE_MAX,1);
    rejected(&a,lan_a,38,2);
    a.storage[0].identity[0][6]='A';rejected(&a,lan_a,38,1);
    initialize(&a,2);
    memcpy(a.storage[1].identity[0],lan_a,39);rejected(&a,lan_a,38,1);
    initialize(&a,2);a.members[0].identity[0].data=(const unsigned char *)UINTPTR_MAX;
    rejected(&a,lan_a,38,1);
    initialize(&a,2);a.storage[0].identity_size[0]=SIZE_MAX;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.storage[0].address_size=SIZE_MAX;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.data.numeric_count=SIZE_MAX;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.data.id.data=(const unsigned char *)UINTPTR_MAX;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.data.members=(SzeroMemberData *)UINTPTR_MAX;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.data.member_count=SIZE_MAX;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.members[0].owner=0;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.members[1].join_order=0;rejected(&a,lan_a,38,1);
    initialize(&a,2);a.storage[1].identity[1][0]=0;rejected(&a,lan_a,38,1);
    initialize(&a,2);native_self.value[0].size=65;rejected(&a,lan_a,38,1);
    native_self=before;native_self.value[1].size=UINT64_MAX;rejected(&a,lan_a,38,1);
    native_self=before;native_self.value[0].bytes[0]=0;rejected(&a,lan_a,38,1);
    native_self=before;native_self.value[0].size=38;memcpy(native_self.value[0].bytes,lan_b,38);
    rejected(&a,lan_a,38,1);
    native_self=before;
    initialize(&a,8);
    unsigned char last[39];memcpy(last,a.storage[7].identity[0],39);
    assert(szero_lan_identity_project(&a,last,38,&native_self,1));
    for(size_t i=0;i<7;i++)assert(szero_lan_identity_valid(a.members[i].identity[0].data,38));
    assert(a.members[7].identity[0].size==17);
    initialize(&a,8);a.data.capacity=7;rejected(&a,lan_a,38,1);
    initialize(&a,8);memcpy(a.storage[7].identity[0],lan_a,39);rejected(&a,lan_a,38,1);
    assert(!szero_lan_identity_project(NULL,lan_a,38,&native_self,1));
    assert(!szero_lan_identity_project(&a,lan_a,38,NULL,1));
    puts("LAN identity projection contracts passed");return 0;
}
