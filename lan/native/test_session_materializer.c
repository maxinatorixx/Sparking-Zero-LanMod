/* Synthetic constructor contract fixture, NOT a game/runtime integration test.
 * cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
 *    native_session_wire.c session_materializer.c test_session_materializer.c \
 *    -o /tmp/szero-materializer-test
 */
#include "session_materializer.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static unsigned calls;
static int simulate_error;
static const SzeroSessionData *expected;
static struct {
    unsigned char texts[1+2+SZERO_MATERIALIZER_MAX_MEMBERS*4][SZERO_MATERIALIZER_MAX_TEXT + 1];
    size_t sizes[1+2+SZERO_MATERIALIZER_MAX_MEMBERS*4], text_count;
    int32_t numeric[SZERO_MATERIALIZER_MAX_NUMERIC];
    uint64_t strong, weak;
} copy;

static SzeroText text(const char *value) {
    SzeroText result = {(const unsigned char *)value, strlen(value)};
    return result;
}

static void check_string(const SzeroNativeString *native, SzeroText value) {
    const unsigned char *bytes;
    size_t size;
    if (native->words[0] & 1) {
        assert(native->words[0] == 1);
        bytes = (const unsigned char *)native->words[1];
        size = native->words[2];
        assert(native->words[3] == size);
    } else {
        bytes = (const unsigned char *)native + 1;
        size = ((const unsigned char *)native)[0] >> 2;
    }
    assert(size == value.size && !memcmp(bytes, value.data, size));
    assert(bytes[size] == 0);
    size_t index = copy.text_count++;
    assert(index < 1+2+SZERO_MATERIALIZER_MAX_MEMBERS*4);
    copy.sizes[index] = size;
    memcpy(copy.texts[index], bytes, size + 1);
}

static SzeroNativeResult *SZERO_NATIVE_CALL fixture_factory(
    SzeroNativeResult *out, uintptr_t unused, SzeroNativeResult *input) {
    calls++;
    assert(unused == 0 && input->tag == 2 && input->payload[0]);
    if (simulate_error) {
        out->tag = 1;
        out->payload[0] = 0x1234; /* Opaque fixture error, caller retains it. */
        return out;
    }
    const SzeroNativeDescriptor *descriptor = (const void *)input->payload[0];
    memset(&copy, 0, sizeof(copy));
    check_string(&descriptor->id, expected->id);
    assert(descriptor->properties.buckets == (uintptr_t)&descriptor->properties.inline_bucket);
    assert(descriptor->properties.bucket_count == 1);
    assert(!descriptor->properties.count && !descriptor->properties.chain &&
           !descriptor->properties.inline_bucket);
    assert(descriptor->settings.compatibility == expected->compatibility);
    assert(descriptor->settings.numeric_count == expected->numeric_count);
    assert(descriptor->settings.numeric_capacity == expected->numeric_count);
    assert(!descriptor->settings.numeric_allocator && !descriptor->settings.stream &&
           !descriptor->settings.stream_allocator);
    assert(descriptor->settings.capacity == expected->capacity);
    if (expected->numeric_count)
        memcpy(copy.numeric, (const void *)descriptor->settings.numeric,
               expected->numeric_count * sizeof(int32_t));
    assert(descriptor->members.count == expected->member_count);
    assert(descriptor->member_count == expected->member_count);
    assert(descriptor->field_e1 == expected->field_e1);
    const SzeroNativeMemberNode *sentinel = (const void *)&descriptor->members;
    const SzeroNativeMemberNode *node = descriptor->members.next, *previous = sentinel;
    for (size_t i = 0; i < expected->member_count; ++i) {
        const SzeroMemberData *member = expected->members + i;
        assert(node != sentinel && node->previous == previous);
        check_string(&node->value.id, member->id);
        for (size_t j = 0; j < 2; ++j) check_string(node->value.identity + j, member->identity[j]);
        check_string(&node->value.address, member->address);
        assert(node->value.join_order == member->join_order);
        assert(node->value.field_88 == member->field_88);
        assert(node->value.optional_present == member->optional_present);
        assert(node->value.optional_value == member->optional_value);
        assert(node->value.field_8b == member->field_8b && node->value.owner == member->owner);
        if (member->owner)
            for (size_t j = 0; j < 2; ++j)
                check_string(descriptor->owner_identity + j, member->identity[j]);
        previous = node;
        node = node->next;
    }
    assert(node == sentinel && descriptor->members.previous == previous);
    copy.strong = copy.weak = 1;
    out->tag = 2;
    /* Distinct fixture-owned output, not a native object or game controlblock. */
    out->payload[0] = (uintptr_t)&copy;
    out->payload[1] = (uintptr_t)&copy.strong;
    return out;
}

static void reject(const SzeroSessionData *data, int code) {
    unsigned old = calls;
    SzeroNativeResult out = {0};
    assert(szero_materialize_session(data, fixture_factory, &out) == code);
    assert(calls == old && out.tag == 0);
    for (size_t i = 0; i < 5; ++i) assert(!out.payload[i]);
}

/* Ordinary host ABI for Python's end-to-end DATA fixture. The callback remains
 * the synthetic Win64-ABI function above; never resolves a game address. */
int szero_fixture_materialize(const SzeroSessionData *data, SzeroNativeResult *output) {
    expected = data;
    simulate_error = 0;
    return szero_materialize_session(data, fixture_factory, output);
}

int main(void) {
    SzeroMemberData members[2] = {0};
    members[0].id = text("creator");
    members[1].id = text("guest-0123456789012345678901234567890123456789");
    for (size_t i = 0; i < 2; ++i) {
        members[i].identity[0] = text(i ? "identity-guest" : "identity-creator");
        members[i].identity[1] = text("identity-second-value");
        members[i].address = text("127.0.0.1:33001");
        members[i].join_order = i;
        members[i].field_88 = (uint8_t)(4 + i);
        members[i].optional_present = 1;
        members[i].optional_value = (uint8_t)(7 + i);
        members[i].field_8b = (uint8_t)(9 + i);
    }
    members[0].owner = 1;
    int32_t numbers[3] = {INT32_MIN, 0, INT32_MAX};
    SzeroSessionData data = {0};
    data.profile = 1;
    data.id = text("0123456789abcdef0123456789abcdef");
    data.compatibility = UINT32_MAX;
    data.numeric = numbers;
    data.numeric_count = 3;
    data.members = members;
    data.member_count = data.capacity = 2;
    data.field_e1 = 0x7f;
    expected = &data;
    SzeroNativeResult out = {0};
    assert(szero_materialize_session(&data, fixture_factory, &out) == SZERO_MATERIALIZED);
    assert(out.tag == 2 && copy.strong == 1 && copy.weak == 1 && calls == 1);
    assert(!memcmp(copy.numeric, numbers, sizeof(numbers)));
    /* Source arena is already freed. Output copies remain readable under ASan. */
    assert(!strcmp((const char *)copy.texts[0], "0123456789abcdef0123456789abcdef"));
    assert(!strcmp((const char *)copy.texts[7], "guest-0123456789012345678901234567890123456789"));
    assert(szero_materialize_session(&data, fixture_factory, &out) == SZERO_MATERIALIZE_INVALID);
    assert(calls == 1); /* Never overwrite caller-owned output. */

    data.profile = 0;
    reject(&data, SZERO_MATERIALIZE_UNSUPPORTED);
    data.profile = 1;
    data.has_stream = 1;
    reject(&data, SZERO_MATERIALIZE_UNSUPPORTED);
    data.has_stream = 0;
    data.has_properties = 1;
    reject(&data, SZERO_MATERIALIZE_UNSUPPORTED);
    data.has_properties = 0;
    data.capacity = 3;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    data.capacity = 2;
    data.member_count = 3;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    data.member_count = 2;
    members[1].join_order = 0;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    members[1].join_order = 1;
    members[0].join_order = 2;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    members[0].join_order = 0;
    SzeroText guest_id = members[1].id;
    members[1].id = members[0].id;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    members[1].id = guest_id;
    members[1].owner = 1;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    members[0].owner = members[1].owner = 0;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    members[0].owner = 1;
    members[1].optional_present = 2;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    members[1].optional_present = 1;
    data.numeric_count = SZERO_MATERIALIZER_MAX_NUMERIC + 1;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    data.numeric_count = 3;
    data.numeric = NULL;
    reject(&data, SZERO_MATERIALIZE_INVALID);
    data.numeric = numbers;
    data.id = (SzeroText){(const unsigned char *)"bad\0id", 6};
    reject(&data, SZERO_MATERIALIZE_INVALID);
    data.id = (SzeroText){(const unsigned char *)"too long", SZERO_MATERIALIZER_MAX_TEXT + 1};
    reject(&data, SZERO_MATERIALIZE_INVALID);
    data.id = text("ok");
    data.member_count = 1;
    data.numeric_count = 0;
    data.numeric = NULL;
    expected = &data;
    unsigned char bounded[SZERO_MATERIALIZER_MAX_TEXT + 1];
    memset(bounded, 'x', sizeof(bounded));
    for (size_t size = 30; size <= SZERO_MATERIALIZER_MAX_TEXT;
         size = size == 30 ? 31 : SZERO_MATERIALIZER_MAX_TEXT) {
        data.id = (SzeroText){bounded, size};
        memset(&out, 0, sizeof(out));
        assert(szero_materialize_session(&data, fixture_factory, &out) == SZERO_MATERIALIZED);
        if (size == SZERO_MATERIALIZER_MAX_TEXT) break;
    }
    data.id = text("ok");
    memset(&out, 0, sizeof(out));
    assert(szero_materialize_session(&data, fixture_factory, &out) == SZERO_MATERIALIZED);
    simulate_error = 1;
    memset(&out, 0, sizeof(out));
    assert(szero_materialize_session(&data, fixture_factory, &out) == SZERO_MATERIALIZE_NATIVE_RESULT);
    assert(out.tag == 1 && out.payload[0] == 0x1234);
    puts("Materializer layout, deep-copy handoff, limits and rejection contracts passed (synthetic native factory only)");
    return 0;
}
