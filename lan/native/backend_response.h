/* SHA-bound native HTTP projection. No authentication or service-cache writes. */
#ifndef SZERO_BACKEND_RESPONSE_H
#define SZERO_BACKEND_RESPONSE_H
#include <stddef.h>
#include <stdint.h>

#define SZERO_BACKEND_BODY_MAX 65536u
#define SZERO_BACKEND_PROJECTED_SIZE 72u

typedef struct {
    uintptr_t buckets;
    uint64_t bucket_count;
    uint64_t count;
    uintptr_t head;
    uintptr_t inline_bucket;
} SzeroBackendHeaders;

typedef struct { uintptr_t allocator,object; } SzeroBackendOwner;
typedef struct {
    uint32_t status,padding;
    SzeroBackendHeaders headers;
    SzeroBackendOwner stream;
} SzeroBackendRaw;

/* Original 146d36f80 view allocated by native 14591c800. Body is borrowed;
 * release destroys/frees the native object, never the body. */
typedef struct {
    uintptr_t vtable;
    uint64_t reserved,read_cursor,size;
    uintptr_t data;
} SzeroBackendView;

typedef struct {
    void *context;
    /* Must allocate an original, writable 40B view through the audited native
     * factory. NULL means allocation refusal. Factory/native function pointers
     * must be SHA/prefix/thread checked by the integration before entry here. */
    SzeroBackendView *(*create_view)(void *);
    /* Original14593dbb0: consumes bytes synchronously; may return a native
     * parser error. Writes exactly the original tagged72 output contract.
     * It may move headers/stream ownership from raw; cleanup sees that state. */
    void (*project)(void *,void *,SzeroBackendRaw *);
    /* Original14228bab0 and1458ac920 respectively. Exactly once, even if
     * projection returned an error; moved-from native values are valid. */
    void (*release_stream)(void *,SzeroBackendOwner *);
    void (*release_headers)(void *,SzeroBackendHeaders *);
} SzeroBackendResponseFunctions;

/* Caller owns readable, immutable body bytes until this synchronous call
 * returns, and exclusive writable output>=72B. Refusal leaves output alone.
 * Return1 ONLY means the original projector ran, NOT successful JSON/login.
 * Content/status are not fabricated: this helper is ONLY for an actual bounded
 * HTTP200 response already received from the explicitly configured LAN server.
 * The transport/integration must validate that origin and status before calling.
 */
int szero_backend_response_project(void *output,size_t output_size,
    const unsigned char *body,size_t body_size,
    const SzeroBackendResponseFunctions *functions);
#endif
