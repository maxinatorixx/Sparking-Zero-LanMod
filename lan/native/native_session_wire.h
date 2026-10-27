/* Exact-build DATA marshalling, not a network protocol or a native hook.
 * No pointer, allocator or vtable is serialized in these wire structures.
 * The host must verify the supported game image before supplying image_base.
 */
#ifndef SZERO_NATIVE_SESSION_WIRE_H
#define SZERO_NATIVE_SESSION_WIRE_H
#include <stddef.h>
#include <stdint.h>
#include "native_bindings.h"

#define SZERO_WIRE_MAX_NUMERIC 32
#define SZERO_WIRE_MAX_STREAM 4096
#define SZERO_WIRE_MAX_TEXT 255
#define SZERO_STREAM_VTABLE_RVA (szero_bind_rva((uintptr_t)0x7b43f10))
#define SZERO_VECTOR_STREAM_VTABLE_RVA (szero_bind_rva((uintptr_t)0x7b43960))
#define SZERO_EMBEDDED_STREAM_VTABLE_RVA (szero_bind_rva((uintptr_t)0x6d15840))
#define SZERO_INLINE64_STREAM_VTABLE_RVA (szero_bind_rva((uintptr_t)0x6d15df0))
#define SZERO_VIEW_STREAM_VTABLE_RVA (szero_bind_rva((uintptr_t)0x6d36f80))

typedef struct {
    uint8_t present;
    uint64_t size, read_cursor, write_cursor;
    unsigned char bytes[SZERO_WIRE_MAX_STREAM];
} SzeroStreamWire;
/* Limited profile policy: read_cursor <= size and write_cursor <= size.
 * Native write positions beyond length can cause growth; they are rejected
 * as unsupported rather than inventing additional payload bytes. */

typedef struct {
    uint32_t compatibility;
    uint64_t numeric_count;
    int32_t numeric[SZERO_WIRE_MAX_NUMERIC];
    uint8_t capacity;
    SzeroStreamWire stream;
} SzeroSettingsWire;

/* Return nonzero only if all requested bytes were copied. May be backed by
 * ReadProcessMemory in the host; fixtures use bounded owned-memory readers.
 * Native object pointers must not escape the capture call to a worker. */
typedef int (*SzeroWireRead)(uintptr_t source, void *output, size_t size, void *user);

enum {
    SZERO_WIRE_OK = 0,
    SZERO_WIRE_INVALID = 1,
    SZERO_WIRE_UNSUPPORTED_STREAM = 2,
    SZERO_WIRE_UNREADABLE = 3
};

/* Exact inline147b43f10/kind1, vector147b43960, embedded146d15840,
 * allocator-less inline146d15df0/kind1, and borrowed40B view146d36f80
 * layouts are admitted.
 * Unknown implementations are
 * rejected rather than dereferenced under an assumed layout. Output is left
 * unchanged on failure. Padding/allocator/capacity slack is not captured. */
int szero_capture_settings(uintptr_t source, uintptr_t image_base,
    SzeroWireRead read, void *user, SzeroSettingsWire *output);

enum { SZERO_STREAM_NONE, SZERO_STREAM_INLINE, SZERO_STREAM_VECTOR, SZERO_STREAM_UNKNOWN,
    SZERO_STREAM_EMBEDDED, SZERO_STREAM_INLINE64, SZERO_STREAM_VIEW };
enum { SZERO_STREAM_REFUSAL_NONE, SZERO_STREAM_REFUSAL_HEADER,
    SZERO_STREAM_REFUSAL_VTABLE, SZERO_STREAM_REFUSAL_KIND,
    SZERO_STREAM_REFUSAL_LENGTH, SZERO_STREAM_REFUSAL_READ_CURSOR,
    SZERO_STREAM_REFUSAL_WRITE_CURSOR, SZERO_STREAM_REFUSAL_DATA };
typedef struct {
    uint32_t layout, refusal, vtable_rva, kind;
    uint64_t size, read_cursor, write_cursor;
} SzeroStreamInfo;
/* Optional scalar diagnostics are written even on refusal. No raw pointer,
 * allocator, identity or payload escapes. vtable_rva is a bounded module-
 * relative static offset, zero for an out-of-image/absent table. */
int szero_capture_settings_info(uintptr_t source, uintptr_t image_base,
    SzeroWireRead read, void *user, SzeroSettingsWire *output, SzeroStreamInfo *info);

typedef struct { uint64_t size; unsigned char bytes[SZERO_WIRE_MAX_TEXT]; } SzeroTextWire;
typedef struct { SzeroTextWire value[2]; } SzeroIdentityWire;
/* Capture exactly two known native strings supplied by the title user object.
 * This does not locate accounts or interpret the values as names/tickets.
 * The caller resolves the legitimate pair on the native thread; never log its
 * raw contents. Long strings and embedded NULs are rejected, not truncated. */
int szero_capture_identity_pair(uintptr_t source, SzeroWireRead read,
    void *user, SzeroIdentityWire *output);

typedef struct {
    SzeroIdentityWire identity;
    SzeroTextWire address;
    uint8_t field_88, optional_present, optional_value, field_8b, owner;
} SzeroMemberWire;
/* Exact two-member descriptor profile only. Finds the local member by the
 * legitimate source identity pair, NOT display name or an invented ID. Reads
 * the bounded native list and preserves original member flags. The caller
 * owns native-thread/lifecycle/binding guards; no native pointers escape here. */
int szero_capture_local_member(uintptr_t descriptor, const SzeroIdentityWire *identity,
    SzeroWireRead read, void *user, SzeroMemberWire *output);

/* Source-only borrowed concrete stream. The game copies it synchronously;
 * NEVER invoke a native destructor on this arena or hand its ownership off.
 * Both cursor values and every payload byte are retained without decoding. */
typedef struct {
    uintptr_t vtable, reserved;
    uint64_t read_cursor, write_cursor;
    uint32_t kind, padding;
    uintptr_t data;
    uint64_t size, capacity;
    uintptr_t allocator;
    unsigned char bytes[SZERO_WIRE_MAX_STREAM];
} SzeroBorrowedStream;

int szero_validate_stream(const SzeroStreamWire *stream);
int szero_borrow_stream(const SzeroStreamWire *stream, uintptr_t image_base,
    SzeroBorrowedStream *output);
#endif
