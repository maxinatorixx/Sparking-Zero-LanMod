#ifndef SZERO_NATIVE_SESSION_INSPECT_H
#define SZERO_NATIVE_SESSION_INSPECT_H
#include "session_materializer.h"
/* Read-only diagnostics, never an admission decision. All unknown values are
 * -1. copy_mask zero means the checked DTO fields agree, NOT full validity. */
typedef struct {
    int read_ok, numeric_pass, self_exclusion, owner_equal, copy_mask;
} SzeroSessionInspection;
enum {
    SZERO_INSPECT_ID=1, SZERO_INSPECT_COMPATIBILITY=2,
    SZERO_INSPECT_NUMERIC_COUNT=4, SZERO_INSPECT_NUMERIC_VALUES=8,
    SZERO_INSPECT_OWNER_PRIMARY=16, SZERO_INSPECT_CAPACITY=32,
    SZERO_INSPECT_MEMBER_COUNT=64
};
void szero_native_session_inspect(uintptr_t descriptor, uintptr_t query,
    const SzeroSessionData *expected, const SzeroTextWire *local_primary,
    int default_normalize, SzeroWireRead read, void *user,
    SzeroSessionInspection *out);
#endif
