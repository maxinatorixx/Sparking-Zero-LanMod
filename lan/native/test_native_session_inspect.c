#include "native_session_inspect.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    SzeroNativeDescriptor descriptor;
    unsigned char query[80],filters[256],pairs[512],long_text[256];
    int32_t numeric[32];
} Memory;
static void put64(void *p,uint64_t n) {memcpy(p,&n,8);}
static void put32(void *p,int32_t n) {memcpy(p,&n,4);}
static int read_mem(uintptr_t p,void *out,size_t n,void *user) {
    uintptr_t first=(uintptr_t)user;
    if(p<first || p-first>sizeof(Memory) || n>sizeof(Memory)-(p-first)) return 0;
    memcpy(out,(const void *)p,n);return 1;
}
static void small(SzeroNativeString *out,const char *value) {
    size_t n=strlen(value);assert(n<=30);memset(out,0,sizeof(*out));
    unsigned char *bytes=(unsigned char *)out;bytes[0]=(unsigned char)(n<<2);
    memcpy(bytes+1,value,n);
}
static void filter(unsigned char *out,uint64_t key,int comparison,int value) {
    put64(out,key);put32(out+8,comparison);put32(out+12,value);
}
int main(void) {
    Memory memory={0};
    int32_t numbers[]={-5,10};
    SzeroMemberData member={0};member.owner=1;
    member.identity[0]=(SzeroText){(const unsigned char *)"primary",7};
    member.identity[1]=(SzeroText){(const unsigned char *)"different-secondary",19};
    SzeroSessionData dto={0};dto.id=(SzeroText){(const unsigned char *)"session",7};
    dto.compatibility=1001;dto.capacity=2;dto.members=&member;dto.member_count=1;
    dto.numeric=numbers;dto.numeric_count=2;
    SzeroNativeDescriptor *d=&memory.descriptor;
    small(&d->id,"session");small(d->owner_identity,"primary");
    d->settings.compatibility=1001;d->settings.capacity=2;
    d->settings.numeric=(uintptr_t)memory.numeric;
    d->settings.numeric_count=d->settings.numeric_capacity=2;
    memcpy(memory.numeric,numbers,sizeof(numbers));d->member_count=1;
    put32(memory.query,1001);memory.query[0x4d]=1;memory.query[0x4e]=255;
    put64(memory.query+8,(uintptr_t)memory.filters);put64(memory.query+0x10,1);
    put64(memory.query+0x18,1);
    filter(memory.filters,0,1,-4); /* -5 < -4, signed */
    SzeroTextWire local={0};local.size=7;memcpy(local.bytes,"primary",7);
    SzeroSessionInspection out;
#define RUN() szero_native_session_inspect((uintptr_t)d,(uintptr_t)memory.query,&dto,&local,0,read_mem,&memory,&out)
    Memory before=memory;RUN();assert(!memcmp(&memory,&before,sizeof(memory)));
    assert(out.read_ok==1 && out.numeric_pass==1 && out.copy_mask==0 &&
        out.owner_equal==1 && out.self_exclusion==1);
    /* Only primary identity participates, irrespective of secondary. */
    small(d->owner_identity+1,"other-secondary");RUN();assert(out.owner_equal==1);
    memory.query[0x4d]=0;RUN();assert(out.self_exclusion==0);
    memory.query[0x4d]=1;local.bytes[0]='x';RUN();assert(out.owner_equal==0 && out.self_exclusion==0);
    local.bytes[0]='p';
    local.size=0;small(d->owner_identity,"");RUN();
    assert(out.owner_equal==1 && out.self_exclusion==0);
    local.size=7;small(d->owner_identity,"primary");
    memory.numeric[0]=9;RUN();assert(out.read_ok && !out.numeric_pass && out.copy_mask==SZERO_INSPECT_NUMERIC_VALUES);
    memory.numeric[0]=-5;
    /* OR pair: false || true; then both false. Missing key is permissive. */
    put64(memory.query+0x28,(uintptr_t)memory.pairs);put64(memory.query+0x30,1);put64(memory.query+0x38,1);
    filter(memory.pairs,0,3,0);filter(memory.pairs+16,1,4,10);RUN();assert(out.numeric_pass==1);
    filter(memory.pairs+16,1,3,10);RUN();assert(out.numeric_pass==0);
    filter(memory.pairs+16,UINT64_MAX,0,4);RUN();assert(out.numeric_pass==1);
    filter(memory.pairs+16,1,5,4);RUN();assert(!out.read_ok && out.numeric_pass==-1);
    put64(memory.query+0x30,0);
    put32(memory.query,2001);RUN();assert(out.numeric_pass==0);
    memory.query[0x4e]=1;RUN();assert(out.numeric_pass==1);
    memory.query[0x4e]=0;RUN();assert(out.numeric_pass==0);
    put32(memory.query,0);RUN();assert(out.numeric_pass==1);
    /* Copy-mask fields are independent of query rejection. */
    d->settings.compatibility=11;d->settings.capacity=1;d->member_count=2;
    small(&d->id,"bad");small(d->owner_identity,"bad");
    d->settings.numeric_count=1;memory.numeric[0]=3;RUN();
    assert(out.copy_mask==127);
    /* Length/capacity and pointer arithmetic guards. */
    d->settings.numeric_count=33;RUN();assert(!out.read_ok);
    d->settings.numeric_count=2;d->settings.numeric=(uintptr_t)(UINTPTR_MAX-2);RUN();assert(!out.read_ok);
    d->settings.numeric=(uintptr_t)memory.numeric;
    put64(memory.query+0x10,17);RUN();assert(!out.read_ok);
    put64(memory.query+0x10,1);put64(memory.query+8,UINTPTR_MAX-4);RUN();assert(!out.read_ok);
    put64(memory.query+8,(uintptr_t)memory.filters);
    d->owner_identity[0].words[0]=1;d->owner_identity[0].words[1]=UINTPTR_MAX-4;
    d->owner_identity[0].words[2]=20;d->owner_identity[0].words[3]=20;
    RUN();assert(!out.read_ok);
    d->owner_identity[0].words[2]=256;d->owner_identity[0].words[3]=256;RUN();assert(!out.read_ok);
    small(d->owner_identity,"primary");
    szero_native_session_inspect(UINTPTR_MAX-8,(uintptr_t)memory.query,&dto,&local,0,read_mem,&memory,&out);
    assert(!out.read_ok && out.copy_mask==-1);
    szero_native_session_inspect((uintptr_t)d,0,&dto,NULL,0,read_mem,&memory,&out);
    assert(out.read_ok && out.owner_equal==-1 && out.self_exclusion==-1 && out.numeric_pass==-1);
    local.size=256;RUN();assert(!out.read_ok);
    puts("native descriptor inspection contracts passed");return 0;
}
