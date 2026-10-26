/* Owned search-result construction. Caller supplies exact-build guarded native
 * callbacks; no engine allocator or destructor is replaced with the CRT. */
#ifndef SZERO_NATIVE_SESSION_SEARCH_H
#define SZERO_NATIVE_SESSION_SEARCH_H
#include "native_session_adapter.h"

typedef struct {
    SzeroNativeSessionCallbacks session;
    /* Must use the original global allocator, alignment 8, because the title's
     * vector destructor frees nonzero-capacity storage through that allocator. */
    void *(*allocate_vector)(void *context, size_t bytes, size_t alignment);
} SzeroNativeSearchCallbacks;

/* Bounded directory profile supports zero or one descriptor. data==NULL iff
 * count==0. Empty results represent actual finite server snapshots, never an
 * acknowledgement of a still-pending operation. Success owns {data,count,cap}
 * at result+8, tag2. The title consumes that storage and nested descriptor.
 * Native errors own their payload. On other failures out stays unchanged.
 * A rejected unknown pair remains quarantined, as in the session adapter.
 * Search does NOT cache/localize a candidate or join it implicitly. */
int szero_native_session_search(const SzeroNativeSearchCallbacks *callbacks,
    const SzeroSessionData *data, size_t count, SzeroNativeResult *empty_out);
#endif
