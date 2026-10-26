/* Guarded Windows callback binding; no DLL entry, hook or network operation.
 * The owner must have asynchronously verified the exact shipping SHA-256 and
 * published its immutable service vptr clone before enabling this context. */
#ifndef SZERO_NATIVE_SESSION_HOST_H
#define SZERO_NATIVE_SESSION_HOST_H
#include "native_session_adapter.h"

typedef struct {
    uintptr_t image_base, service, expected_vptr;
    uint32_t native_thread_id;
    uint8_t exact_hash_verified;
    void *vptr_owner;
    int (*owns_vptr)(void *owner, uintptr_t service, uintptr_t vptr);
    /* Caller may inspect these bounded reason codes, never raw identities. */
    uint32_t last_error;
} SzeroNativeSessionHost;
enum { SZERO_HOST_OK=0, SZERO_HOST_CONFIG=1, SZERO_HOST_IMAGE=2,
       SZERO_HOST_THREAD=3, SZERO_HOST_CONTEXT=4, SZERO_HOST_VPTR=5,
       SZERO_HOST_FUNCTION=6, SZERO_HOST_PAIR=7 };

int szero_native_session_host_ready(SzeroNativeSessionHost *host);
/* Fills callback table only. Does NOT claim native readiness or invoke game. */
int szero_native_session_host_bind(SzeroNativeSessionHost *host,
    const SzeroStreamWire *stream, SzeroNativeSessionCallbacks *output);
#endif
