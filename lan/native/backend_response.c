#include "backend_response.h"
#include <string.h>

_Static_assert(sizeof(uintptr_t)==8,"native backend requires 64-bit ABI");
_Static_assert(sizeof(SzeroBackendHeaders)==40,"native headers size");
_Static_assert(sizeof(SzeroBackendOwner)==16,"native owner size");
_Static_assert(sizeof(SzeroBackendView)==40,"native view size");
_Static_assert(offsetof(SzeroBackendView,read_cursor)==16,"view cursor");
_Static_assert(offsetof(SzeroBackendView,size)==24,"view extent");
_Static_assert(offsetof(SzeroBackendView,data)==32,"view bytes");
_Static_assert(sizeof(SzeroBackendRaw)==64,"raw HTTP size");
_Static_assert(offsetof(SzeroBackendRaw,headers)==8,"raw headers");
_Static_assert(offsetof(SzeroBackendRaw,stream)==48,"raw stream");

int szero_backend_response_project(void *output,size_t output_size,
    const unsigned char *body,size_t body_size,
    const SzeroBackendResponseFunctions *functions) {
    SzeroBackendRaw raw;
    SzeroBackendView *view;
    if (!output || output_size<SZERO_BACKEND_PROJECTED_SIZE || !body ||
        !body_size || body_size>SZERO_BACKEND_BODY_MAX ||
        (uintptr_t)body>UINTPTR_MAX-(body_size-1) ||
        (uintptr_t)output>UINTPTR_MAX-(SZERO_BACKEND_PROJECTED_SIZE-1) ||
        !functions || !functions->create_view || !functions->project ||
        !functions->release_stream || !functions->release_headers) return 0;
    view=functions->create_view(functions->context);
    if (!view) return 0;
    /* Do not copy this initialized value: map.buckets refers into raw. */
    memset(&raw,0,sizeof(raw));
    raw.status=200;
    raw.headers.buckets=(uintptr_t)&raw.headers.inline_bucket;
    raw.headers.bucket_count=1;
    raw.stream.object=(uintptr_t)view;
    view->reserved=0;
    view->read_cursor=0;
    view->size=body_size;
    view->data=(uintptr_t)body;
    functions->project(functions->context,output,&raw);
    functions->release_stream(functions->context,&raw.stream);
    functions->release_headers(functions->context,&raw.headers);
    return 1;
}
