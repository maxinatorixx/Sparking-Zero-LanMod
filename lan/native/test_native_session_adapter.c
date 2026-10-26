/* Portable injected-ABI fixture. Does not execute the game's allocator. */
#include "native_session_adapter.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static int ready_value=1, error_value, step, calls;
static int expect_stream;
static int transaction, releases, destroyed_strings;
static SzeroNativeDescriptor descriptor;
static uintptr_t control=123;
static int valid_pair_value=1;
static int validate_pair(void *ctx, const uintptr_t pair[2]) {
    assert(ctx==&step && pair[0]==(uintptr_t)&descriptor && pair[1]==(uintptr_t)&control);
    return valid_pair_value;
}
static int ready(void *ctx) { assert(ctx==&step); return ready_value; }
static SzeroNativeResult *SZERO_NATIVE_CALL factory(SzeroNativeResult *out,
    uintptr_t unused, SzeroNativeResult *in) {
    assert(unused==0 && in->tag==2); calls++;
    if(error_value) {
        out->tag=1; out->payload[0]=0x1234;
        out->payload[1]=0x80; out->payload[2]=0x5678;
        return out;
    }
    assert(step++==0);
    const SzeroNativeDescriptor *src=(const void *)in->payload[0];
    if(expect_stream) {
        const SzeroBorrowedStream *s=(const void *)src->settings.stream;
        assert(s && s->vtable==0x140000000ULL+SZERO_STREAM_VTABLE_RVA);
        assert(s->size==3 && s->read_cursor==1 && s->write_cursor==2);
        assert(!memcmp((const void *)s->data,"abc",3));
    } else assert(!src->settings.stream);
    /* Fixture only retains POD ID; no fake borrowed arena survives factory. */
    descriptor.id=src->id;
    out->tag=2; out->payload[0]=(uintptr_t)&descriptor;
    out->payload[1]=(uintptr_t)&control;
    return out;
}
static void localize(void *ctx, uintptr_t d) {
    assert(ctx==&step && d==(uintptr_t)&descriptor && step++==1);
}
static void copy_string(void *ctx, SzeroNativeString *out, SzeroText txt) {
    assert(ctx==&step && step++==2 && txt.size<30);
    memset(out,0,sizeof(*out));
    ((unsigned char *)out)[0]=(unsigned char)(txt.size<<2);
    memcpy((unsigned char *)out+1,txt.data,txt.size);
}
static void cache(void *ctx, uintptr_t pair[2]) {
    assert(ctx==&step && (step==2 || step==3));
    assert(pair[0]==(uintptr_t)&descriptor && pair[1]==(uintptr_t)&control);
    step=4; /* Simulate original helper leaving caller's consumed words. */
}
static void release(void *ctx, uintptr_t pair[2]) {
    assert(ctx==&step && (transaction || step==3));
    step++; releases++;
    assert(pair[0]==(uintptr_t)&descriptor && pair[1]==(uintptr_t)&control);
}
static void destroy_string(void *ctx,SzeroNativeString *owned) {
    assert(ctx==&step && transaction);
    assert(((unsigned char *)owned)[0]);
    destroyed_strings++;
    memset(owned,0,sizeof(*owned));
}
static void clone(void *ctx, SzeroNativeDescriptor *out, uintptr_t source) {
    assert(ctx==&step && step++==2 && source==(uintptr_t)&descriptor);
    memset(out,0,sizeof(*out)); out->id=descriptor.id;
}
static void diff(void *ctx, SzeroNativeDescriptor *owned, uint8_t settings) {
    assert(ctx==&step && step++==4 && settings==1);
    assert(!memcmp(&owned->id,&descriptor.id,sizeof(owned->id)));
    memset(owned,0,sizeof(*owned));
}
static SzeroText text(const char *s) {
    SzeroText t={(const unsigned char *)s,strlen(s)}; return t;
}
int main(void) {
    SzeroNativeSessionCallbacks cb={0};
    cb.context=&step; cb.ready=ready; cb.factory=factory;
    cb.validate_pair=validate_pair;
    cb.localize=localize; cb.copy_string=copy_string; cb.cache_consume=cache;
    cb.release_pair=release; cb.clone_descriptor=clone; cb.diff_consume=diff;
    cb.destroy_string=destroy_string;
    SzeroMemberData member={0};
    member.id=text("member"); member.identity[0]=text("legitimate-user");
    member.identity[1]=text("legitimate-secondary"); member.address=text("127.0.0.1:1234");
    member.owner=1;
    SzeroSessionData data={0};
    data.profile=1; data.id=text("server-session"); data.capacity=2;
    data.members=&member; data.member_count=1;
    SzeroNativeResult out={0};
    assert(szero_native_session_create(&cb,&data,&out)==SZERO_ADAPTER_OK);
    assert(step==4 && out.tag==2);
    assert(((unsigned char *)out.payload)[0]==(data.id.size<<2));
    assert(!memcmp((unsigned char *)out.payload+1,data.id.data,data.id.size));
    struct { SzeroNativeError out; uint64_t canary; } join={0};
    join.canary=UINT64_C(0xfeeddeadbeef1234); step=0;
    assert(szero_native_session_join(&cb,&data,&join.out)==SZERO_ADAPTER_OK);
    assert(step==4 && join.out.code==0 && join.canary==UINT64_C(0xfeeddeadbeef1234));
    memset(&out,0,sizeof(out)); step=0;
    assert(szero_native_session_refresh(&cb,&data,&out)==SZERO_ADAPTER_OK);
    assert(step==5 && out.tag==0);
    error_value=1; step=0;
    assert(szero_native_session_create(&cb,&data,&out)==SZERO_ADAPTER_NATIVE_ERROR);
    assert(out.tag==1 && out.payload[0]==0x1234 && out.payload[1]==0x80 && step==0);
    memset(&join.out,0,sizeof(join.out));
    assert(szero_native_session_join(&cb,&data,&join.out)==SZERO_ADAPTER_NATIVE_ERROR);
    assert(join.out.code==0x1234 && join.out.text.words[0]==0x80);
    assert(join.canary==UINT64_C(0xfeeddeadbeef1234));
    memset(&out,0,sizeof(out));
    assert(szero_native_session_refresh(&cb,&data,&out)==SZERO_ADAPTER_NATIVE_ERROR);
    assert(out.tag==1 && out.payload[2]==0x5678 && step==0);
    int oldcalls=calls; memset(&out,0,sizeof(out)); ready_value=0;
    assert(szero_native_session_create(&cb,&data,&out)==SZERO_ADAPTER_NOT_READY);
    assert(calls==oldcalls && !out.tag);
    ready_value=1; out.tag=9;
    assert(szero_native_session_create(&cb,&data,&out)==SZERO_ADAPTER_INVALID);
    assert(calls==oldcalls && out.tag==9);
    memset(&out,0,sizeof(out)); data.has_properties=1;
    assert(szero_native_session_create(&cb,&data,&out)==SZERO_ADAPTER_MATERIALIZE);
    assert(calls==oldcalls && !out.tag);
    data.has_properties=0; data.profile=2; data.has_stream=1;
    SzeroStreamWire stream={0}; stream.present=1; stream.size=3;
    stream.read_cursor=1; stream.write_cursor=2; memcpy(stream.bytes,"abc",3);
    cb.stream=&stream; cb.image_base=0x140000000ULL;
    error_value=0; expect_stream=1; step=0;
    assert(szero_native_session_create(&cb,&data,&out)==SZERO_ADAPTER_OK);
    assert(out.tag==2 && step==4);
    memset(&out,0,sizeof(out)); valid_pair_value=0; step=0;
    assert(szero_native_session_create(&cb,&data,&out)==SZERO_ADAPTER_NATIVE_LAYOUT);
    assert(!out.tag && step==1); /* No localize/cache/free of untrusted pair. */
    valid_pair_value=1; expect_stream=0; cb.stream=NULL;
    data.profile=1; data.has_stream=0; transaction=1;
    SzeroNativeSessionStage stage={0}; memset(&out,0,sizeof(out)); step=0;
    assert(szero_native_session_prepare(&cb,&data,1,&stage,&out)==SZERO_ADAPTER_OK);
    assert(stage.state==SZERO_STAGE_PREPARED && step==3 && !out.tag);
    assert(szero_native_session_prepare(&cb,&data,1,&stage,&out)==SZERO_ADAPTER_INVALID);
    ready_value=0;
    assert(szero_native_session_commit(&cb,&stage,&out)==SZERO_ADAPTER_NOT_READY);
    assert(stage.state==SZERO_STAGE_PREPARED && step==3 && !out.tag);
    ready_value=1; int old_releases=releases;
    assert(szero_native_session_abort(&cb,&stage)==SZERO_ADAPTER_OK);
    assert(stage.state==SZERO_STAGE_ABORTED && releases==old_releases+1 && destroyed_strings==1);
    assert(szero_native_session_abort(&cb,&stage)==SZERO_ADAPTER_OK);
    assert(releases==old_releases+1 && destroyed_strings==1);
    assert(szero_native_session_commit(&cb,&stage,&out)==SZERO_ADAPTER_INVALID);
    memset(&stage,0,sizeof(stage)); step=0;
    assert(szero_native_session_prepare(&cb,&data,1,&stage,&out)==SZERO_ADAPTER_OK);
    assert(szero_native_session_commit(&cb,&stage,&out)==SZERO_ADAPTER_OK);
    assert(stage.state==SZERO_STAGE_COMMITTED && out.tag==2 && step==4);
    assert(szero_native_session_abort(&cb,&stage)==SZERO_ADAPTER_INVALID);
    assert(releases==old_releases+1 && destroyed_strings==1);
    memset(&stage,0,sizeof(stage)); memset(&out,0,sizeof(out)); step=0;
    assert(szero_native_session_prepare(&cb,&data,0,&stage,&out)==SZERO_ADAPTER_OK);
    assert(stage.state==SZERO_STAGE_PREPARED && step==2);
    memset(&join.out,0,sizeof(join.out));
    assert(szero_native_session_commit(&cb,&stage,&join.out)==SZERO_ADAPTER_OK);
    assert(stage.state==SZERO_STAGE_COMMITTED && step==4 && join.out.code==0);
    assert(join.canary==UINT64_C(0xfeeddeadbeef1234));
    memset(&stage,0,sizeof(stage)); step=0;
    assert(szero_native_session_prepare(&cb,&data,0,&stage,&out)==SZERO_ADAPTER_OK);
    assert(szero_native_session_abort(&cb,&stage)==SZERO_ADAPTER_OK);
    assert(releases==old_releases+2 && destroyed_strings==1);
    puts("native session adapter injected-ABI contracts passed");
    return 0;
}
