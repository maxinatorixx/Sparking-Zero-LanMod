#include "native_session_codec.h"
#include <string.h>

typedef struct { const unsigned char *cursor, *end; } Reader;
typedef struct { const unsigned char *data; size_t size; } Token;

static int next(Reader *reader, Token *out) {
    if (reader->cursor >= reader->end || *reader->cursor == ' ') return 0;
    const unsigned char *first = reader->cursor;
    while (reader->cursor < reader->end && *reader->cursor != ' ') reader->cursor++;
    out->data = first;
    out->size = (size_t)(reader->cursor - first);
    if (reader->cursor < reader->end) {
        reader->cursor++;
        /* No trailing space, double spaces or empty tokens. */
        if (reader->cursor == reader->end || *reader->cursor == ' ') return 0;
    }
    return out->size != 0;
}

static int uint_token(Token token, uint64_t maximum, uint64_t *out) {
    if (!token.size || (token.size > 1 && token.data[0] == '0')) return 0;
    uint64_t value = 0;
    for (size_t i = 0; i < token.size; ++i) {
        unsigned char ch = token.data[i];
        if (ch < '0' || ch > '9') return 0;
        uint64_t digit = (uint64_t)(ch - '0');
        if (digit > maximum || value > (maximum - digit) / 10) return 0;
        value = value * 10 + digit;
    }
    *out = value;
    return 1;
}

static int number(Reader *reader, uint64_t maximum, uint64_t *out) {
    Token token;
    return next(reader, &token) && uint_token(token, maximum, out);
}

static int signed_number(Reader *reader, int32_t *out) {
    Token token;
    if (!next(reader, &token)) return 0;
    int negative = token.size && token.data[0] == '-';
    if (negative) { token.data++; token.size--; }
    uint64_t value;
    if (!uint_token(token, negative ? UINT64_C(2147483648) : INT32_MAX, &value) ||
        (negative && !value)) return 0;
    *out = negative ? (int32_t)(-(int64_t)value) : (int32_t)value;
    return 1;
}

static int nibble(unsigned char ch) {
    if (ch >= '0' && ch <= '9') return ch - '0';
    if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
    return -1;
}

static int identifier(Reader *reader, unsigned char out[33]) {
    Token token;
    if (!next(reader, &token) || token.size != 32) return 0;
    for (size_t i = 0; i < 32; ++i) if (nibble(token.data[i]) < 0) return 0;
    memcpy(out, token.data, 32);
    out[32] = 0;
    return 1;
}

static int hex_bytes(Token token, unsigned char *out, size_t count, int text) {
    if (token.size != count * 2) return 0;
    for (size_t i = 0; i < count; ++i) {
        int high = nibble(token.data[i * 2]), low = nibble(token.data[i * 2 + 1]);
        if (high < 0 || low < 0) return 0;
        unsigned char byte = (unsigned char)((high << 4) | low);
        if (text && !byte) return 0;
        out[i] = byte;
    }
    return 1;
}

static int text(Reader *reader, unsigned char *out, size_t *size) {
    Token token;
    if (!next(reader, &token) || !token.size || token.size % 2 ||
        token.size > SZERO_SESSION_CODEC_TEXT * 2) return 0;
    *size = token.size / 2;
    if (!hex_bytes(token, out, *size, 1)) return 0;
    out[*size] = 0;
    return 1;
}

static void rebase(SzeroSessionCodec *decoded) {
    decoded->data.id = (SzeroText){decoded->id, 32};
    decoded->data.numeric = decoded->data.numeric_count ? decoded->numeric : NULL;
    decoded->data.members = decoded->members;
    for (size_t i = 0; i < decoded->data.member_count; ++i) {
        SzeroMemberData *member = decoded->members + i;
        SzeroSessionCodecMemberStorage *storage = decoded->storage + i;
        member->id = (SzeroText){storage->id, 32};
        for (size_t j = 0; j < 2; ++j)
            member->identity[j] = (SzeroText){storage->identity[j], storage->identity_size[j]};
        member->address = (SzeroText){storage->address, storage->address_size};
    }
}

int szero_session_decode(const unsigned char *frame, size_t size,
    SzeroSessionCodec *output) {
    if (!frame || !output || !size || size > SZERO_SESSION_FRAME_MAX ||
        frame[size - 1] != '\n') return SZERO_SESSION_CODEC_INVALID;
    for (size_t i = 0; i + 1 < size; ++i)
        if (frame[i] < 0x20 || frame[i] > 0x7e) return SZERO_SESSION_CODEC_INVALID;
    Reader reader = {frame, frame + size - 1};
    Token token;
    SzeroSessionCodec decoded = {0};
    uint64_t value;
    if (!next(&reader, &token) || token.size != 8 ||
        (memcmp(token.data, "SESSION3", 8) && memcmp(token.data, "SESSION4", 8)))
        return SZERO_SESSION_CODEC_INVALID;
    int multi=token.data[7]=='4';
    if (
        !identifier(&reader, decoded.id) || !number(&reader, UINT32_MAX, &value))
        return SZERO_SESSION_CODEC_INVALID;
    decoded.data.profile = 2;
    decoded.data.compatibility = (uint32_t)value;
    if (!number(&reader, SZERO_SESSION_CODEC_NUMERIC, &value)) return SZERO_SESSION_CODEC_INVALID;
    decoded.data.numeric_count = (size_t)value;
    for (size_t i = 0; i < decoded.data.numeric_count; ++i)
        if (!signed_number(&reader, decoded.numeric + i)) return SZERO_SESSION_CODEC_INVALID;
    if (!number(&reader, multi?SZERO_MATERIALIZER_MAX_MEMBERS:2, &value) ||
        !value || (!multi && value!=2)) return SZERO_SESSION_CODEC_INVALID;
    decoded.data.capacity = (uint8_t)value;
    if (!number(&reader, UINT8_MAX, &value)) return SZERO_SESSION_CODEC_INVALID;
    decoded.data.field_e1 = (uint8_t)value;
    if (!number(&reader, 1, &value)) return SZERO_SESSION_CODEC_INVALID;
    decoded.stream.present = decoded.data.has_stream = (uint8_t)value;
    if (!number(&reader, SZERO_WIRE_MAX_STREAM, &decoded.stream.size) ||
        !number(&reader, UINT64_MAX, &decoded.stream.read_cursor) ||
        !number(&reader, UINT64_MAX, &decoded.stream.write_cursor) ||
        !next(&reader, &token)) return SZERO_SESSION_CODEC_INVALID;
    if (decoded.stream.size) {
        if (!decoded.stream.present ||
            !hex_bytes(token, decoded.stream.bytes, (size_t)decoded.stream.size, 0))
            return SZERO_SESSION_CODEC_INVALID;
    } else if (token.size != 1 || token.data[0] != '-') return SZERO_SESSION_CODEC_INVALID;
    if (!decoded.stream.present &&
        (decoded.stream.size || decoded.stream.read_cursor || decoded.stream.write_cursor))
        return SZERO_SESSION_CODEC_INVALID;
    if (!number(&reader, decoded.data.capacity, &value) || !value) return SZERO_SESSION_CODEC_INVALID;
    decoded.data.member_count = (size_t)value;
    unsigned owners = 0;
    for (size_t i = 0; i < decoded.data.member_count; ++i) {
        SzeroMemberData *member = decoded.members + i;
        SzeroSessionCodecMemberStorage *storage = decoded.storage + i;
        if (!identifier(&reader, storage->id) ||
            !number(&reader, UINT64_MAX, &member->join_order) ||
            !text(&reader, storage->identity[0], storage->identity_size) ||
            !text(&reader, storage->identity[1], storage->identity_size + 1) ||
            !text(&reader, storage->address, &storage->address_size) ||
            !number(&reader, UINT8_MAX, &value)) return SZERO_SESSION_CODEC_INVALID;
        member->field_88 = (uint8_t)value;
        if (!number(&reader, 1, &value)) return SZERO_SESSION_CODEC_INVALID;
        member->optional_present = (uint8_t)value;
        if (!number(&reader, UINT8_MAX, &value)) return SZERO_SESSION_CODEC_INVALID;
        member->optional_value = (uint8_t)value;
        if (!number(&reader, 0, &value) || !number(&reader, 1, &value))
            return SZERO_SESSION_CODEC_INVALID;
        member->owner = (uint8_t)value;
        owners += member->owner;
        if (i && member->join_order <= decoded.members[i - 1].join_order)
            return SZERO_SESSION_CODEC_INVALID;
        for(size_t j=0;j<i;j++)
            if(!memcmp(storage->id,decoded.storage[j].id,32))return SZERO_SESSION_CODEC_INVALID;
    }
    if (owners != 1 || reader.cursor != reader.end) return SZERO_SESSION_CODEC_INVALID;
    *output = decoded;
    rebase(output);
    return SZERO_SESSION_CODEC_OK;
}
