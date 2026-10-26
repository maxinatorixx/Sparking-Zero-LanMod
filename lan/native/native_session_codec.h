/* Pointer-free SESSION3 transport decoder. SOURCE ONLY; never calls the game. */
#ifndef SZERO_NATIVE_SESSION_CODEC_H
#define SZERO_NATIVE_SESSION_CODEC_H
#include "native_session_adapter.h"

#define SZERO_SESSION_FRAME_MAX 16384
#define SZERO_SESSION_CODEC_NUMERIC 16
#define SZERO_SESSION_CODEC_TEXT 64

typedef struct {
    unsigned char id[33];
    unsigned char identity[2][SZERO_SESSION_CODEC_TEXT + 1];
    unsigned char address[SZERO_SESSION_CODEC_TEXT + 1];
    size_t identity_size[2], address_size;
} SzeroSessionCodecMemberStorage;

typedef struct {
    SzeroSessionData data;
    SzeroStreamWire stream;
    int32_t numeric[SZERO_SESSION_CODEC_NUMERIC];
    SzeroMemberData members[SZERO_MATERIALIZER_MAX_MEMBERS];
    unsigned char id[33];
    SzeroSessionCodecMemberStorage storage[SZERO_MATERIALIZER_MAX_MEMBERS];
} SzeroSessionCodec;

enum { SZERO_SESSION_CODEC_OK = 0, SZERO_SESSION_CODEC_INVALID = 1 };

/* Canonical ASCII, single spaces, one terminating LF, no trailing bytes/NUL.
 * Every value is validated before committing; failure leaves output unchanged.
 * Success data pointers refer to output's OWN storage. Do not memcpy/move the
 * structure after decoding, nor overwrite it while a synchronous native caller
 * borrows its values. Re-decoding into exclusively-owned output is permitted.
 * No native ownership is stored here and no destructor is needed.
 * Cursor syntax is unsigned64; reconstruction policy remains independently
 * checked by szero_materialize_session_stream, never silently normalized. */
int szero_session_decode(const unsigned char *frame, size_t size,
    SzeroSessionCodec *output);
#endif
