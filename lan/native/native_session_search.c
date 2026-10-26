#include "native_session_search.h"
#include <string.h>

_Static_assert(sizeof(SzeroNativeDescriptor)==0xe8,"search descriptor stride");
_Static_assert(sizeof(SzeroNativeResult)==48,"search result ABI");
static int empty(const void *p,size_t n) {
    const unsigned char *bytes=p;
    for(size_t i=0;i<n;i++) if(bytes[i]) return 0;
    return 1;
}
int szero_native_session_search(const SzeroNativeSearchCallbacks *callbacks,
    const SzeroSessionData *data,size_t count,SzeroNativeResult *out) {
    if(!callbacks || !out || !empty(out,sizeof(*out)) || count>1 ||
       (count==0 ? data!=NULL : data==NULL)) return SZERO_ADAPTER_INVALID;
    const SzeroNativeSessionCallbacks *cb=&callbacks->session;
    if(!cb->ready || !cb->factory || !cb->validate_pair ||
       !cb->release_pair || !cb->clone_descriptor || !callbacks->allocate_vector)
        return SZERO_ADAPTER_INVALID;
    if(!cb->ready(cb->context)) return SZERO_ADAPTER_NOT_READY;
    if(count==0) { out->tag=2; return SZERO_ADAPTER_OK; }
    SzeroNativeResult handle={0};
    int rc=cb->stream ? szero_materialize_session_stream(data,cb->stream,
        cb->image_base,cb->factory,&handle) :
        szero_materialize_session(data,cb->factory,&handle);
    if(rc==SZERO_MATERIALIZE_NATIVE_RESULT && handle.tag==1) {
        *out=handle; return SZERO_ADAPTER_NATIVE_ERROR;
    }
    if(rc!=SZERO_MATERIALIZED) return SZERO_ADAPTER_MATERIALIZE;
    uintptr_t pair[2]={handle.payload[0],handle.payload[1]};
    if(!cb->validate_pair(cb->context,pair)) {
        if(cb->quarantine_pair) cb->quarantine_pair(cb->context,pair);
        return SZERO_ADAPTER_NATIVE_LAYOUT;
    }
    SzeroNativeDescriptor *owned=callbacks->allocate_vector(cb->context,sizeof(*owned),8);
    if(!owned) { cb->release_pair(cb->context,pair); return SZERO_ADAPTER_MATERIALIZE; }
    memset(owned,0,sizeof(*owned));
    cb->clone_descriptor(cb->context,owned,pair[0]);
    cb->release_pair(cb->context,pair);
    /* No borrowed source remains: clone owns every nested native field. */
    out->payload[0]=(uintptr_t)owned;
    out->payload[1]=1;
    out->payload[2]=1;
    out->tag=2;
    return SZERO_ADAPTER_OK;
}
