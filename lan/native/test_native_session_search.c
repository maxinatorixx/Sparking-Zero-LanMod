#include "native_session_search.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
static int stage,fail_alloc,invalid_pair,native_error,ready_value=1;
static SzeroNativeDescriptor source;
static int ready(void *ctx) { assert(ctx==&stage); return ready_value; }
static SzeroNativeResult *SZERO_NATIVE_CALL factory(SzeroNativeResult *out,
    uintptr_t unused,SzeroNativeResult *in) {
    assert(!unused && in->tag==2 && stage++==0);
    if(native_error) { out->tag=1; out->payload[0]=0x413; return out; }
    const SzeroNativeDescriptor *borrowed=(const void *)in->payload[0];
    assert(((unsigned char *)&borrowed->id)[0]==(7<<2));
    memset(&source,0,sizeof(source)); source.field_e1=17;
    out->tag=2; out->payload[0]=(uintptr_t)&source; out->payload[1]=123;
    return out;
}
static int valid(void *ctx,const uintptr_t pair[2]) {
    assert(ctx==&stage && stage++==1 && pair[0]==(uintptr_t)&source && pair[1]==123);
    return !invalid_pair;
}
static void *allocate(void *ctx,size_t size,size_t alignment) {
    assert(ctx==&stage && stage++==2 && size==0xe8 && alignment==8);
    return fail_alloc ? NULL : malloc(size); /* Test allocator, never game. */
}
static void clone(void *ctx,SzeroNativeDescriptor *out,uintptr_t ptr) {
    assert(ctx==&stage && stage++==3 && ptr==(uintptr_t)&source);
    assert(out!=&source); memcpy(out,&source,sizeof(*out));
}
static void release(void *ctx,uintptr_t pair[2]) {
    assert(ctx==&stage && stage++==(fail_alloc?3:4));
    assert(pair[0]==(uintptr_t)&source && pair[1]==123);
    memset(&source,0,sizeof(source));
}
static SzeroText text(const char *s) { SzeroText t={(const unsigned char *)s,strlen(s)}; return t; }
int main(void) {
    SzeroNativeSearchCallbacks cb={0}; cb.session.context=&stage;
    cb.session.ready=ready; cb.session.factory=factory;
    cb.session.validate_pair=valid; cb.session.clone_descriptor=clone;
    cb.session.release_pair=release; cb.allocate_vector=allocate;
    SzeroMemberData member={0}; member.id=text("member");
    member.identity[0]=text("identity"); member.identity[1]=text("second");
    member.address=text("127.0.0.1:1234"); member.owner=1;
    SzeroSessionData data={0}; data.profile=1; data.id=text("session");
    data.capacity=2; data.members=&member; data.member_count=1;
    struct { SzeroNativeResult out; uint64_t canary; } result={0};
    result.canary=UINT64_C(0xbeefdead12345678);
    assert(szero_native_session_search(&cb,&data,1,&result.out)==SZERO_ADAPTER_OK);
    assert(stage==5 && result.out.tag==2 && result.out.payload[1]==1 && result.out.payload[2]==1);
    assert(((SzeroNativeDescriptor *)result.out.payload[0])->field_e1==17);
    assert(result.canary==UINT64_C(0xbeefdead12345678));
    free((void *)result.out.payload[0]); memset(&result.out,0,sizeof(result.out));
    stage=0; assert(szero_native_session_search(&cb,NULL,0,&result.out)==SZERO_ADAPTER_OK);
    assert(!stage && result.out.tag==2 && !result.out.payload[0] && !result.out.payload[1]);
    memset(&result.out,0,sizeof(result.out)); fail_alloc=1;
    assert(szero_native_session_search(&cb,&data,1,&result.out)==SZERO_ADAPTER_MATERIALIZE);
    assert(stage==4 && !result.out.tag); fail_alloc=0; stage=0; invalid_pair=1;
    assert(szero_native_session_search(&cb,&data,1,&result.out)==SZERO_ADAPTER_NATIVE_LAYOUT);
    assert(stage==2 && !result.out.tag); invalid_pair=0; stage=0; native_error=1;
    assert(szero_native_session_search(&cb,&data,1,&result.out)==SZERO_ADAPTER_NATIVE_ERROR);
    assert(stage==1 && result.out.tag==1 && result.out.payload[0]==0x413);
    memset(&result.out,0,sizeof(result.out)); stage=0; native_error=0; ready_value=0;
    assert(szero_native_session_search(&cb,&data,1,&result.out)==SZERO_ADAPTER_NOT_READY);
    assert(!stage && !result.out.tag); ready_value=1;
    assert(szero_native_session_search(&cb,&data,2,&result.out)==SZERO_ADAPTER_INVALID);
    assert(szero_native_session_search(&cb,NULL,1,&result.out)==SZERO_ADAPTER_INVALID);
    assert(szero_native_session_search(&cb,&data,0,&result.out)==SZERO_ADAPTER_INVALID);
    result.out.tag=9;
    assert(szero_native_session_search(&cb,&data,1,&result.out)==SZERO_ADAPTER_INVALID);
    assert(result.out.tag==9 && !stage);
    puts("owned search vector contracts passed");
    return 0;
}
