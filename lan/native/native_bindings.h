#ifndef SZERO_NATIVE_BINDINGS_H
#define SZERO_NATIVE_BINDINGS_H
/* Canonical RVAs identify reviewed operations, never an executable version.
 * Resolve once on the worker before publishing any native callback. */
#include <stdint.h>
#include <stddef.h>
#if (!defined(_WIN32) && !defined(SZERO_BINDINGS_PORTABLE_TEST)) || defined(SZERO_BINDINGS_TEST_IDENTITY) || defined(SZERO_BACKEND_ADAPTER_TEST) || defined(SZERO_SERVICE_TRACE_TEST) || defined(SZERO_NATIVE_SEARCH_TEST) || defined(SZERO_NATIVE_SESSION_IPC_TEST) || defined(SZERO_SESSION_TEST) || defined(SZERO_MENU_TEST) || defined(SZERO_PROBE_TEST)
#define SZERO_BINDINGS_IDENTITY_FIXTURE 1
static inline int szero_bindings_init(uintptr_t base) { return base!=0; }
static inline uintptr_t szero_bind_rva(uintptr_t canonical) { return canonical; }
static inline const char *szero_bindings_error(void) { return "fixture_identity"; }
#ifdef _WIN32
#include <winsock2.h>
#include "native_image.h"
static inline int szero_bind_prefix(uintptr_t base,uintptr_t canonical,const unsigned char *prefix,size_t length) {
    /* Explicit synthetic fixtures use bounded owned memory without PE headers.
     * Their image-verification refusal is tested separately. Production uses
     * the resolved-image implementation below and never takes this branch. */
    unsigned char actual[32];SIZE_T got=0;
    if(!base || !prefix || !length || length>sizeof(actual) ||
       base>UINTPTR_MAX-canonical || base+canonical>UINTPTR_MAX-length)return 0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)(base+canonical),actual,length,&got) &&
           got==length && !memcmp(actual,prefix,length);
}
#endif
#else
int szero_bindings_init(uintptr_t base);
uintptr_t szero_bind_rva(uintptr_t canonical);
const char *szero_bindings_error(void);
#ifdef SZERO_BINDINGS_PORTABLE_TEST
int szero_bindings_init_image(uintptr_t base,size_t accessible);
#endif
int szero_bind_prefix(uintptr_t base,uintptr_t canonical,const unsigned char *prefix,size_t length);
#endif
#endif
