/* Windows gate fixture only: does not call any fabricated native code target. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "native_session_host.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static int owns(void *owner,uintptr_t service,uintptr_t vptr) {
    (void)owner; (void)service; (void)vptr; return 1;
}
static uintptr_t table[6];
int main(void) {
    SzeroNativeSessionHost h={0};
    assert(!szero_native_session_host_ready(NULL));
    assert(!szero_native_session_host_ready(&h) && h.last_error==SZERO_HOST_CONFIG);
    h.image_base=(uintptr_t)GetModuleHandleW(NULL); h.service=1;
    h.expected_vptr=1; h.native_thread_id=GetCurrentThreadId(); h.owns_vptr=owns;
    assert(!szero_native_session_host_ready(&h) && h.last_error==SZERO_HOST_CONFIG);
    h.exact_hash_verified=1; h.image_base++;
    assert(!szero_native_session_host_ready(&h) && h.last_error==SZERO_HOST_IMAGE);
    h.image_base--; h.native_thread_id++;
    assert(!szero_native_session_host_ready(&h) && h.last_error==SZERO_HOST_THREAD);
    h.native_thread_id--;
    /* This tiny fixture has no title context; no callback/game function runs. */
    assert(!szero_native_session_host_ready(&h) && h.last_error==SZERO_HOST_CONTEXT);
    SzeroNativeSessionCallbacks cb={0};
    assert(szero_native_session_host_bind(&h,NULL,&cb));
    assert(!cb.ready(cb.context));
    unsigned char *allocation=VirtualAlloc(NULL,0x100,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    assert(allocation);
    h.image_base=(uintptr_t)table-0x7b99d90;
    assert(szero_native_session_host_bind(&h,NULL,&cb));
    table[4]=h.image_base+0x59263a0; table[5]=h.image_base+0x59263b0;
    uintptr_t pair[2]={(uintptr_t)allocation,(uintptr_t)allocation+0xe8};
    uintptr_t vt=(uintptr_t)table;
    memcpy(allocation+0xe8,&vt,8);
    LONG64 count=1;
    memcpy(allocation+0xf0,&count,8); memcpy(allocation+0xf8,&count,8);
    assert(cb.validate_pair(cb.context,pair));
    pair[1]--;
    assert(!cb.validate_pair(cb.context,pair) && h.last_error==SZERO_HOST_PAIR);
    pair[1]++; table[5]++;
    assert(!cb.validate_pair(cb.context,pair)); table[5]--;
    count=0; memcpy(allocation+0xf0,&count,8);
    assert(!cb.validate_pair(cb.context,pair));
    VirtualFree(allocation,0,MEM_RELEASE);
    puts("native session host rejection and pair gates passed; no game code executed");
    return 0;
}
