#include "native_session_adapter.h"
#include <string.h>

_Static_assert(sizeof(SzeroNativeError)==40, "plain native error ABI");
_Static_assert(sizeof(SzeroNativeResult)==48, "tagged native result ABI");

static int all_zero(const void *p, size_t n) {
    const unsigned char *b=p;
    for(size_t i=0;i<n;i++) if(b[i]) return 0;
    return 1;
}
static int valid(const SzeroNativeSessionCallbacks *cb) {
    return cb && cb->ready && cb->factory && cb->validate_pair && cb->localize && cb->copy_string &&
        cb->cache_consume && cb->release_pair && cb->clone_descriptor && cb->diff_consume;
}
static int construct(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, SzeroNativeResult *result) {
    if(!cb->ready(cb->context)) return SZERO_ADAPTER_NOT_READY;
    int rc=cb->stream ? szero_materialize_session_stream(data,cb->stream,
        cb->image_base,cb->factory,result) :
        szero_materialize_session(data,cb->factory,result);
    if(rc==SZERO_MATERIALIZE_NATIVE_RESULT && result->tag==1)
        return SZERO_ADAPTER_NATIVE_ERROR;
    if(rc!=SZERO_MATERIALIZED) return SZERO_ADAPTER_MATERIALIZE;
    uintptr_t pair[2]={result->payload[0],result->payload[1]};
    if(!cb->validate_pair(cb->context,pair)) {
        if(cb->quarantine_pair) cb->quarantine_pair(cb->context,pair);
        return SZERO_ADAPTER_NATIVE_LAYOUT;
    }
    cb->localize(cb->context,result->payload[0]);
    return SZERO_ADAPTER_OK;
}
static void cache(const SzeroNativeSessionCallbacks *cb, SzeroNativeResult *handle) {
    uintptr_t pair[2]={handle->payload[0],handle->payload[1]};
    cb->cache_consume(cb->context,pair);
    /* The native cache takes ownership but leaves stale caller words. */
    memset(handle,0,sizeof(*handle));
}
int szero_native_session_create(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, SzeroNativeResult *out) {
    if(!valid(cb)||!data||!out||!all_zero(out,sizeof(*out))) return SZERO_ADAPTER_INVALID;
    SzeroNativeResult handle={0};
    int rc=construct(cb,data,&handle);
    if(rc==SZERO_ADAPTER_NATIVE_ERROR) { *out=handle; return rc; }
    if(rc!=SZERO_ADAPTER_OK) return rc;
    SzeroNativeString id={{0}};
    cb->copy_string(cb->context,&id,data->id);
    cache(cb,&handle);
    memcpy(out->payload,&id,sizeof(id));
    out->tag=2;
    return SZERO_ADAPTER_OK;
}
int szero_native_session_join(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, SzeroNativeError *out) {
    if(!valid(cb)||!data||!out||!all_zero(out,sizeof(*out))) return SZERO_ADAPTER_INVALID;
    SzeroNativeResult handle={0};
    int rc=construct(cb,data,&handle);
    if(rc==SZERO_ADAPTER_NATIVE_ERROR) {
        memcpy(out,handle.payload,sizeof(*out));
        return rc;
    }
    if(rc!=SZERO_ADAPTER_OK) return rc;
    cache(cb,&handle);
    /* Original local join converts a tag2 zero-code result to plain code0. */
    memset(out,0,sizeof(*out));
    return SZERO_ADAPTER_OK;
}
int szero_native_session_refresh(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, SzeroNativeResult *out) {
    if(!valid(cb)||!data||!out||!all_zero(out,sizeof(*out))) return SZERO_ADAPTER_INVALID;
    SzeroNativeResult handle={0};
    int rc=construct(cb,data,&handle);
    if(rc==SZERO_ADAPTER_NATIVE_ERROR) { *out=handle; return rc; }
    if(rc!=SZERO_ADAPTER_OK) return rc;
    SzeroNativeDescriptor owned={0};
    cb->clone_descriptor(cb->context,&owned,handle.payload[0]);
    uintptr_t pair[2]={handle.payload[0],handle.payload[1]};
    cb->release_pair(cb->context,pair);
    memset(&handle,0,sizeof(handle));
    cb->diff_consume(cb->context,&owned,1);
    /* Diff unconditionally destroys the moved temporary; no second dtor. */
    memset(&owned,0,sizeof(owned));
    return SZERO_ADAPTER_OK;
}

int szero_native_session_prepare(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, int create, SzeroNativeSessionStage *stage,
    SzeroNativeResult *out) {
    if(!valid(cb) || !cb->destroy_string || !data || !stage || !out ||
       (create!=0 && create!=1) || !all_zero(stage,sizeof(*stage)) ||
       !all_zero(out,sizeof(*out))) return SZERO_ADAPTER_INVALID;
    SzeroNativeResult handle={0};
    int rc=construct(cb,data,&handle);
    if(rc==SZERO_ADAPTER_NATIVE_ERROR) { *out=handle; return rc; }
    if(rc!=SZERO_ADAPTER_OK) return rc;
    /* No callback can observe this descriptor through service cache yet. */
    SzeroNativeString id={{0}};
    if(create) cb->copy_string(cb->context,&id,data->id);
    stage->handle=handle;
    stage->id=id;
    stage->create=(uint8_t)create;
    stage->state=SZERO_STAGE_PREPARED;
    return SZERO_ADAPTER_OK;
}

int szero_native_session_commit(const SzeroNativeSessionCallbacks *cb,
    SzeroNativeSessionStage *stage, void *out) {
    if(!valid(cb) || !stage || !out || stage->state!=SZERO_STAGE_PREPARED ||
       !all_zero(out,stage->create?sizeof(SzeroNativeResult):sizeof(SzeroNativeError)))
        return SZERO_ADAPTER_INVALID;
    if(!cb->ready(cb->context)) return SZERO_ADAPTER_NOT_READY;
    uintptr_t pair[2]={stage->handle.payload[0],stage->handle.payload[1]};
    if(!cb->validate_pair(cb->context,pair)) return SZERO_ADAPTER_NATIVE_LAYOUT;
    cache(cb,&stage->handle);
    if(stage->create) {
        SzeroNativeResult *result=out;
        memcpy(result->payload,&stage->id,sizeof(stage->id));
        result->tag=2;
        memset(&stage->id,0,sizeof(stage->id));
    } else memset(out,0,sizeof(SzeroNativeError));
    stage->state=SZERO_STAGE_COMMITTED;
    return SZERO_ADAPTER_OK;
}

int szero_native_session_abort(const SzeroNativeSessionCallbacks *cb,
    SzeroNativeSessionStage *stage) {
    if(!valid(cb) || !cb->destroy_string || !stage) return SZERO_ADAPTER_INVALID;
    if(stage->state==SZERO_STAGE_ABORTED) return SZERO_ADAPTER_OK;
    if(stage->state!=SZERO_STAGE_PREPARED) return SZERO_ADAPTER_INVALID;
    if(!cb->ready(cb->context)) return SZERO_ADAPTER_NOT_READY;
    uintptr_t pair[2]={stage->handle.payload[0],stage->handle.payload[1]};
    if(!cb->validate_pair(cb->context,pair)) return SZERO_ADAPTER_NATIVE_LAYOUT;
    cb->release_pair(cb->context,pair);
    memset(&stage->handle,0,sizeof(stage->handle));
    if(stage->create) cb->destroy_string(cb->context,&stage->id);
    memset(&stage->id,0,sizeof(stage->id));
    stage->state=SZERO_STAGE_ABORTED;
    return SZERO_ADAPTER_OK;
}
