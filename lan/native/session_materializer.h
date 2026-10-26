/* Exact-build client-side construction core. SOURCE ONLY: no installed hook.
 * Server data contains values, never any of these process-local pointers.
 * A future host must verify the EXE hash, thread/lifecycle and factory address
 * before supplying the callback. This module does not establish those gates.
 */
#ifndef SZERO_SESSION_MATERIALIZER_H
#define SZERO_SESSION_MATERIALIZER_H
#include <stddef.h>
#include <stdint.h>
#include "native_session_wire.h"

#if defined(__GNUC__) && defined(__x86_64__)
#define SZERO_NATIVE_CALL __attribute__((ms_abi))
#else
#define SZERO_NATIVE_CALL
#endif

#define SZERO_MATERIALIZER_MAX_TEXT 255
#define SZERO_MATERIALIZER_MAX_NUMERIC 32
#define SZERO_MATERIALIZER_MAX_MEMBERS 8
#define SZERO_DESCRIPTOR_SIZE 0xe8
#define SZERO_MEMBER_SIZE 0x90

typedef struct { const unsigned char *data; size_t size; } SzeroText;
typedef struct {
    SzeroText id, identity[2], address;
    uint64_t join_order;
    uint8_t field_88, optional_present, optional_value, field_8b, owner;
} SzeroMemberData;
typedef struct {
    uint32_t profile; /* Explicit profile1 empty stream, or profile2 via stream API. */
    SzeroText id;
    uint32_t compatibility;
    const int32_t *numeric;
    size_t numeric_count;
    const SzeroMemberData *members;
    size_t member_count;
    uint8_t capacity, field_e1;
    /* Required explicit profile: never silently discard unimplemented data. */
    uint8_t has_stream, has_properties;
} SzeroSessionData;

/* Layout recovery: analysis/native-descriptor-construction-trace.txt. */
typedef struct { uint64_t words[4]; } SzeroNativeString;
typedef struct {
    uintptr_t buckets;
    uint64_t bucket_count, count;
    uintptr_t chain, inline_bucket;
} SzeroNativeProperties;
typedef struct {
    uint32_t compatibility, padding;
    uintptr_t numeric;
    uint64_t numeric_count, numeric_capacity;
    uintptr_t numeric_allocator, stream_allocator, stream;
    uint8_t capacity, tail_padding[7];
} SzeroNativeSettings;
typedef struct SzeroNativeMemberNode SzeroNativeMemberNode;
typedef struct {
    SzeroNativeString id;
    uint64_t join_order;
    SzeroNativeString identity[2], address;
    uint8_t field_88, optional_present, optional_value, field_8b, owner, padding[3];
} SzeroNativeMember;
struct SzeroNativeMemberNode {
    SzeroNativeMemberNode *next, *previous;
    SzeroNativeMember value;
};
typedef struct {
    SzeroNativeMemberNode *next, *previous;
    uint64_t count;
} SzeroNativeMemberList;
typedef struct {
    SzeroNativeString id;
    SzeroNativeProperties properties;
    SzeroNativeSettings settings;
    SzeroNativeString owner_identity[2];
    SzeroNativeMemberList members;
    uint8_t member_count, field_e1, padding[6];
} SzeroNativeDescriptor;

/* Success: tag2, pointer at+8, control block pointer at+10. Error union is
 * retained opaquely; the caller must use native ownership-aware cleanup. */
typedef struct {
    uint32_t tag, padding;
    uintptr_t payload[5];
} SzeroNativeResult;
typedef SzeroNativeResult *(SZERO_NATIVE_CALL *SzeroDescriptorFactory)(
    SzeroNativeResult *output, uintptr_t unused, SzeroNativeResult *input);

enum {
    SZERO_MATERIALIZED = 0,
    SZERO_MATERIALIZE_INVALID = 1,
    SZERO_MATERIALIZE_UNSUPPORTED = 2,
    SZERO_MATERIALIZE_NO_MEMORY = 3,
    SZERO_MATERIALIZE_NATIVE_RESULT = 4
};

extern const char szero_materializer_supported_sha256[];
/* output must be empty/unowned on entry. Rejections do not touch it. After
 * factory invocation it belongs to the caller even on a native error result.
 * The factory must deep-copy before returning, as exact-build145943940 does.
 * No source descriptor is handed off: temporary source storage dies on return.
 */
int szero_materialize_session(const SzeroSessionData *data,
    SzeroDescriptorFactory factory, SzeroNativeResult *output);
/* Explicit profile2: same descriptor schema, empty property map, optional
 * bounded opaque stream. The caller verifies image identity before supplying
 * image_base; no image address is accepted from the network. */
int szero_materialize_session_stream(const SzeroSessionData *data,
    const SzeroStreamWire *stream, uintptr_t image_base,
    SzeroDescriptorFactory factory, SzeroNativeResult *output);
#endif
