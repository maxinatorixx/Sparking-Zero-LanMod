/* Canonical protocol contracts only. No game or native allocator execution. */
#include "native_session_codec.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char session[] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static const char member0[] = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
static const char member1[] = "cccccccccccccccccccccccccccccccc";

static const char valid[] =
    "SESSION3 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 4294967295 3 -2147483648 0 2147483647 "
    "2 255 1 4 1 4 00ff10a5 2 "
    "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 0 616263 646566 3132372e302e302e313a31 255 1 255 0 1 "
    "cccccccccccccccccccccccccccccccc 1 78 79 7a 0 0 0 0 0\n";

static void reject(const unsigned char *frame, size_t size) {
    SzeroSessionCodec output;
    memset(&output, 0xa5, sizeof(output));
    SzeroSessionCodec unchanged = output;
    assert(szero_session_decode(frame, size, &output) == SZERO_SESSION_CODEC_INVALID);
    assert(!memcmp(&output, &unchanged, sizeof(output)));
}

static void replace_reject(const char *needle, const char *replacement) {
    const char *at = strstr(valid, needle);
    assert(at);
    char frame[SZERO_SESSION_FRAME_MAX + 1];
    size_t prefix = (size_t)(at - valid), suffix = strlen(at + strlen(needle));
    size_t size = prefix + strlen(replacement) + suffix;
    assert(size < sizeof(frame));
    memcpy(frame, valid, prefix);
    memcpy(frame + prefix, replacement, strlen(replacement));
    memcpy(frame + prefix + strlen(replacement), at + strlen(needle), suffix);
    reject((const unsigned char *)frame, size);
}

int main(int argc, char **argv) {
    /* Optional bounded stdin decoding makes the same compiled production
     * parser available to Python's real server-DTO fixture, without a second
     * independent parser or any game/native callback. */
    if (argc == 2 && !strcmp(argv[1], "--decode")) {
        unsigned char frame[SZERO_SESSION_FRAME_MAX + 1];
        size_t size = fread(frame, 1, sizeof(frame), stdin);
        SzeroSessionCodec decoded;
        if (ferror(stdin) || szero_session_decode(frame, size, &decoded)) return 2;
        printf("%u %zu %zu %u %llu %llu %llu\n", decoded.data.compatibility,
            decoded.data.numeric_count, decoded.data.member_count, decoded.stream.present,
            (unsigned long long)decoded.stream.size,
            (unsigned long long)decoded.stream.read_cursor,
            (unsigned long long)decoded.stream.write_cursor);
        for (size_t i = 0; i < decoded.stream.size; ++i) printf("%02x", decoded.stream.bytes[i]);
        puts("");
        return 0;
    }
    SzeroSessionCodec decoded;
    assert(!szero_session_decode((const unsigned char *)valid, strlen(valid), &decoded));
    assert(decoded.data.profile == 2 && decoded.data.compatibility == UINT32_MAX);
    assert(decoded.data.numeric_count == 3 && decoded.data.numeric == decoded.numeric);
    assert(decoded.numeric[0] == INT32_MIN && decoded.numeric[1] == 0 && decoded.numeric[2] == INT32_MAX);
    assert(decoded.data.members == decoded.members && decoded.data.member_count == 2);
    assert(decoded.data.capacity == 2 && decoded.data.field_e1 == 255);
    assert(decoded.data.id.data == decoded.id && decoded.data.id.size == 32);
    assert(!memcmp(decoded.id, session, 32));
    assert(decoded.data.has_stream && decoded.stream.present && decoded.stream.size == 4);
    assert(decoded.stream.read_cursor == 1 && decoded.stream.write_cursor == 4);
    assert(!memcmp(decoded.stream.bytes, "\0\xff\x10\xa5", 4));
    for (size_t i = 0; i < 2; ++i) {
        assert(decoded.members[i].id.data == decoded.storage[i].id);
        assert(decoded.members[i].identity[0].data == decoded.storage[i].identity[0]);
        assert(decoded.members[i].identity[1].data == decoded.storage[i].identity[1]);
        assert(decoded.members[i].address.data == decoded.storage[i].address);
        assert(!decoded.members[i].field_8b && decoded.members[i].owner == (i == 0));
    }
    assert(!memcmp(decoded.members[0].id.data, member0, 32));
    assert(!memcmp(decoded.members[1].id.data, member1, 32));
    assert(decoded.members[0].optional_present && decoded.members[0].optional_value == 255);
    assert(decoded.members[0].identity[0].size == 3 &&
        !memcmp(decoded.members[0].identity[0].data, "abc", 3));
    /* Generation-independent decode can reuse exclusively-owned output; all
     * internal pointers must now reference that output, never a stack scratch. */
    SzeroSessionCodec other;
    assert(!szero_session_decode((const unsigned char *)valid, strlen(valid), &other));
    assert(other.data.id.data == other.id && other.data.id.data != decoded.data.id.data);

    for (size_t i = 0; i < strlen(valid); ++i) reject((const unsigned char *)valid, i);
    replace_reject("SESSION3", "SESSION5");
    replace_reject("SESSION3 ", "SESSION3  ");
    replace_reject("4294967295", "4294967296");
    replace_reject("4294967295", "04294967295");
    replace_reject(" 3 -2147483648", " 17 -2147483648");
    replace_reject("-2147483648", "-2147483649");
    replace_reject(" 0 2147483647", " -0 2147483647");
    replace_reject("2147483647", "+2147483647");
    replace_reject(" 2 255 1", " 1 255 1");
    replace_reject(" 255 1 4", " 256 1 4");
    replace_reject(" 1 4 1 4 00ff10a5", " 2 4 1 4 00ff10a5");
    replace_reject(" 1 4 1 4 00ff10a5", " 0 4 1 4 00ff10a5");
    replace_reject(" 1 4 1 4 00ff10a5", " 1 4097 1 4 00ff10a5");
    replace_reject(" 1 4 1 4 00ff10a5", " 1 4 18446744073709551616 4 00ff10a5");
    replace_reject("00ff10a5", "00FF10a5");
    replace_reject("00ff10a5", "00ff10a");
    replace_reject("00ff10a5", "-");
    replace_reject(" 2 bbbbb", " 0 bbbbb");
    replace_reject(" 2 bbbbb", " 3 bbbbb");
    replace_reject("bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbB");
    replace_reject("cccccccccccccccccccccccccccccccc 1", "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 1");
    replace_reject("cccccccccccccccccccccccccccccccc 1", "cccccccccccccccccccccccccccccccc 0");
    replace_reject("616263", "610063");
    replace_reject("616263", "61626");
    char oversized_text[131];
    memset(oversized_text, 'a', 130);
    oversized_text[130] = 0;
    replace_reject("616263", oversized_text);
    replace_reject(" 255 1 255 0 1", " 255 2 255 0 1");
    replace_reject(" 255 1 255 0 1", " 255 1 256 0 1");
    replace_reject(" 255 1 255 0 1", " 255 1 255 1 1");
    replace_reject(" 255 1 255 0 1", " 255 1 255 0 0");
    replace_reject(" 0 0 0 0 0\n", " 0 0 0 0 1\n");
    replace_reject("\n", " \n");
    replace_reject("\n", "\r\n");
    replace_reject("\n", "\nextra");
    replace_reject("\n", "\n\n");
    unsigned char bad[sizeof(valid)];
    memcpy(bad, valid, sizeof(valid));
    bad[16] = 0;
    reject(bad, strlen(valid));
    bad[16] = 0x80;
    reject(bad, strlen(valid));
    bad[16] = '\t';
    reject(bad, strlen(valid));
    assert(szero_session_decode(NULL, 10, &decoded));
    assert(szero_session_decode((const unsigned char *)valid, strlen(valid), NULL));
    /* Full u64 cursor syntax is preserved; source-only materialization may
     * explicitly reject this out-of-profile state, never truncate it. */
    char single[2048];
    int length = snprintf(single, sizeof(single),
        "SESSION3 %s 0 0 2 0 1 0 18446744073709551615 18446744073709551615 - 1 "
        "%s 18446744073709551615 78 79 7a 0 0 0 0 1\n", session, member0);
    assert(length > 0 && (size_t)length < sizeof(single));
    assert(!szero_session_decode((const unsigned char *)single, (size_t)length, &decoded));
    assert(decoded.stream.read_cursor == UINT64_MAX && decoded.stream.write_cursor == UINT64_MAX);
    assert(decoded.members[0].join_order == UINT64_MAX);
    assert(!decoded.data.numeric_count && !decoded.data.numeric);
    /* Maximum payload length and all values survive exactly. */
    char maximum[SZERO_SESSION_FRAME_MAX + 1];
    length = snprintf(maximum, sizeof(maximum), "SESSION3 %s 1 0 2 0 1 4096 0 4096 ", session);
    size_t offset = (size_t)length;
    memset(maximum + offset, 'f', 8192);
    offset += 8192;
    length = snprintf(maximum + offset, sizeof(maximum) - offset,
        " 1 %s 0 78 79 7a 0 0 0 0 1\n", member0);
    offset += (size_t)length;
    assert(offset < sizeof(maximum));
    assert(!szero_session_decode((const unsigned char *)maximum, offset, &decoded));
    assert(decoded.stream.size == 4096 && decoded.stream.bytes[0] == 255 && decoded.stream.bytes[4095] == 255);
    reject((const unsigned char *)maximum, SZERO_SESSION_FRAME_MAX + 1);
    puts("SESSION3 codec contracts passed (owned data only)");
    return 0;
}
