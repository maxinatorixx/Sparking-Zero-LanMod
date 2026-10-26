/* SOURCE integration core. Native callbacks must be exact-build/thread guarded
 * by the caller. This is not an installed game hook or a transport bootstrap. */
#ifndef SZERO_NATIVE_SESSION_ADAPTER_H
#define SZERO_NATIVE_SESSION_ADAPTER_H
#include "session_materializer.h"

typedef struct { uint32_t code, padding; SzeroNativeString text; } SzeroNativeError;
typedef struct {
    void *context;
    int (*ready)(void *context);
    SzeroDescriptorFactory factory;
    /* Optional full stream profile; immutable for this synchronous operation. */
    const SzeroStreamWire *stream;
    uintptr_t image_base;
    /* Validate newly returned owned descriptor/control before any native use.
     * Failure is quarantined: never guess how to free an unknown layout. */
    int (*validate_pair)(void *context, const uintptr_t pair[2]);
    /* Localizes legitimate own member, including optional presence/value. */
    void (*localize)(void *context, uintptr_t descriptor);
    void (*copy_string)(void *context, SzeroNativeString *empty_out, SzeroText text);
    /* Consumes exactly one pair reference; source words need not be cleared. */
    void (*cache_consume)(void *context, uintptr_t pair[2]);
    void (*release_pair)(void *context, uintptr_t pair[2]);
    /* Produces independent native ownership, not an arena/shallow copy. */
    void (*clone_descriptor)(void *context, SzeroNativeDescriptor *empty_out,
                             uintptr_t source);
    /* Consumes/destroys every nested field of the temporary, even for no ID. */
    void (*diff_consume)(void *context, SzeroNativeDescriptor *owned, uint8_t settings);
    /* Native owned-string destruction; required by transactional preparation. */
    void (*destroy_string)(void *context, SzeroNativeString *owned);
    /* Retain unknown owned factory pair without dereferencing/freeing it;
     * production dispatcher must disable further allocation after this call. */
    void (*quarantine_pair)(void *context, const uintptr_t pair[2]);
} SzeroNativeSessionCallbacks;

enum { SZERO_ADAPTER_OK=0, SZERO_ADAPTER_INVALID=1,
       SZERO_ADAPTER_NOT_READY=2, SZERO_ADAPTER_MATERIALIZE=3,
       SZERO_ADAPTER_NATIVE_ERROR=4, SZERO_ADAPTER_NATIVE_LAYOUT=5 };

/* Output must be empty/unowned. Rejection before factory leaves it unchanged.
 * Once an owned native error is returned, output belongs to caller.
 * Success CREATE is tag2 + OWNED STRING at+8, NEVER a descriptor handle.
 * Success JOIN is a PLAIN40-byte zero-code error, NEVER a tagged result.
 * Neither function creates a titlewrapper or establishes a channel. */
int szero_native_session_create(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, SzeroNativeResult *empty_out);
int szero_native_session_join(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, SzeroNativeError *empty_out);
int szero_native_session_refresh(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, SzeroNativeResult *empty_error_out);

/* Prepared native ownership is invisible to service cache/title wrappers.
 * Worker may carry only generation/state, NEVER these native pointers. Caller
 * must receive the matching server COMMITTED before calling commit. All three
 * calls run on the guarded native thread; callbacks/context must stay alive.
 * Abort is valid before commit, including cancellation/failed ACK. Commit
 * failure leaves ownership in stage so it can be aborted later. A stage cannot
 * be copied, reused, or silently discarded while state is PREPARED.
 */
enum { SZERO_STAGE_EMPTY=0, SZERO_STAGE_PREPARED=1,
       SZERO_STAGE_COMMITTED=2, SZERO_STAGE_ABORTED=3 };
typedef struct {
    uint32_t state;
    uint8_t create;
    SzeroNativeResult handle;
    SzeroNativeString id;
} SzeroNativeSessionStage;
int szero_native_session_prepare(const SzeroNativeSessionCallbacks *cb,
    const SzeroSessionData *data, int create, SzeroNativeSessionStage *empty_stage,
    SzeroNativeResult *empty_error_out);
int szero_native_session_commit(const SzeroNativeSessionCallbacks *cb,
    SzeroNativeSessionStage *stage, void *empty_out);
int szero_native_session_abort(const SzeroNativeSessionCallbacks *cb,
    SzeroNativeSessionStage *stage);
#endif
