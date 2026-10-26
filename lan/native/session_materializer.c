#include "session_materializer.h"
#include <stdlib.h>
#include <string.h>

const char szero_materializer_supported_sha256[] =
    "e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55";

_Static_assert(sizeof(uintptr_t) == 8, "Only x64 target layout supported");
_Static_assert(sizeof(SzeroNativeString) == 0x20, "String layout");
_Static_assert(sizeof(SzeroNativeProperties) == 0x28, "Property layout");
_Static_assert(sizeof(SzeroNativeSettings) == 0x40, "Settings layout");
_Static_assert(offsetof(SzeroNativeSettings, stream) == 0x30, "Stream offset");
_Static_assert(offsetof(SzeroNativeSettings, capacity) == 0x38, "Capacity offset");
_Static_assert(sizeof(SzeroNativeMember) == SZERO_MEMBER_SIZE, "Member layout");
_Static_assert(sizeof(SzeroNativeMemberNode) == 0xa0, "Node layout");
_Static_assert(offsetof(SzeroNativeMember, address) == 0x68, "Address offset");
_Static_assert(offsetof(SzeroNativeMember, owner) == 0x8c, "Owner offset");
_Static_assert(sizeof(SzeroNativeDescriptor) == SZERO_DESCRIPTOR_SIZE, "Descriptor layout");
_Static_assert(offsetof(SzeroNativeDescriptor, settings) == 0x48, "Settings offset");
_Static_assert(offsetof(SzeroNativeDescriptor, owner_identity) == 0x88, "Identity offset");
_Static_assert(offsetof(SzeroNativeDescriptor, members) == 0xc8, "Members offset");
_Static_assert(offsetof(SzeroNativeDescriptor, member_count) == 0xe0, "Count offset");
_Static_assert(sizeof(SzeroNativeResult) == 0x30, "Result storage");

static int valid_text(SzeroText text, int required) {
    return text.size <= SZERO_MATERIALIZER_MAX_TEXT && (!required || text.size) &&
        (!text.size || (text.data && !memchr(text.data, 0, text.size)));
}

static int same_text(SzeroText a, SzeroText b) {
    return a.size == b.size && (!a.size || !memcmp(a.data, b.data, a.size));
}

static int validate(const SzeroSessionData *data, const SzeroStreamWire *stream) {
    if (!data) return SZERO_MATERIALIZE_INVALID;
    if (data->profile != (stream ? 2u : 1u)) return SZERO_MATERIALIZE_UNSUPPORTED;
    if (!valid_text(data->id, 1) || !data->capacity ||
        data->capacity > SZERO_MATERIALIZER_MAX_MEMBERS || !data->members ||
        !data->member_count || data->member_count > data->capacity ||
        data->numeric_count > SZERO_MATERIALIZER_MAX_NUMERIC ||
        (data->numeric_count && !data->numeric)) return SZERO_MATERIALIZE_INVALID;
    if (data->has_properties || (!stream && data->has_stream))
        return SZERO_MATERIALIZE_UNSUPPORTED;
    if (stream) {
        int validation = szero_validate_stream(stream);
        if (validation == SZERO_WIRE_UNSUPPORTED_STREAM) return SZERO_MATERIALIZE_UNSUPPORTED;
        if (validation || data->has_stream != stream->present) return SZERO_MATERIALIZE_INVALID;
    }
    unsigned owners = 0;
    for (size_t i = 0; i < data->member_count; ++i) {
        const SzeroMemberData *member = data->members + i;
        if (!valid_text(member->id, 1) || !valid_text(member->identity[0], 1) ||
            !valid_text(member->identity[1], 1) || !valid_text(member->address, 1) ||
            member->owner > 1 || member->optional_present > 1)
            return SZERO_MATERIALIZE_INVALID;
        owners += member->owner;
        if (i && member->join_order <= data->members[i - 1].join_order)
            return SZERO_MATERIALIZE_INVALID; /* Native insertion keeps this order. */
        for (size_t j = 0; j < i; ++j)
            if (same_text(member->id, data->members[j].id) ||
                member->join_order == data->members[j].join_order)
                return SZERO_MATERIALIZE_INVALID;
    }
    return owners == 1 ? SZERO_MATERIALIZED : SZERO_MATERIALIZE_INVALID;
}

typedef struct {
    SzeroNativeDescriptor descriptor;
    SzeroNativeMemberNode nodes[SZERO_MATERIALIZER_MAX_MEMBERS];
    /* Copy all source values before invoking native code. No game wrapper
     * may retain this borrowed arena. Only the native-owned copy escapes. */
    unsigned char text[1 + 2 + SZERO_MATERIALIZER_MAX_MEMBERS * 4]
                      [SZERO_MATERIALIZER_MAX_TEXT + 1];
    int32_t numeric[SZERO_MATERIALIZER_MAX_NUMERIC];
    SzeroBorrowedStream stream;
    size_t text_count;
} Source;

static void make_string(Source *source, SzeroNativeString *out, SzeroText text) {
    unsigned char *bytes = source->text[source->text_count++];
    if (text.size) memcpy(bytes, text.data, text.size);
    bytes[text.size] = 0;
    if (text.size < 31) {
        unsigned char *small = (unsigned char *)out;
        small[0] = (unsigned char)(text.size << 2);
        memcpy(small + 1, bytes, text.size + 1);
    } else {
        /* Heap-form SOURCE VIEW: tag1 selects native default allocator when
         *141edf4b0 copies it. The arena is ours, not game-owned: NEVER call
         * the game's string/descriptor destructor on this source view. */
        out->words[0] = 1;
        out->words[1] = (uintptr_t)bytes;
        out->words[2] = text.size;
        out->words[3] = text.size;
    }
}

static int materialize(const SzeroSessionData *data, const SzeroStreamWire *stream,
    uintptr_t image_base, SzeroDescriptorFactory factory, SzeroNativeResult *output) {
    if (!factory || !output) return SZERO_MATERIALIZE_INVALID;
    if (output->tag) return SZERO_MATERIALIZE_INVALID;
    for (size_t i = 0; i < 5; ++i)
        if (output->payload[i]) return SZERO_MATERIALIZE_INVALID;
    int result = validate(data, stream);
    if (result) return result;
    if (stream && (!image_base || image_base > UINTPTR_MAX - SZERO_STREAM_VTABLE_RVA))
        return SZERO_MATERIALIZE_INVALID;
    Source *source = calloc(1, sizeof(*source));
    if (!source) return SZERO_MATERIALIZE_NO_MEMORY;
    SzeroNativeDescriptor *descriptor = &source->descriptor;
    make_string(source, &descriptor->id, data->id);
    descriptor->properties.buckets = (uintptr_t)&descriptor->properties.inline_bucket;
    descriptor->properties.bucket_count = 1;
    descriptor->settings.compatibility = data->compatibility;
    if (data->numeric_count) {
        memcpy(source->numeric, data->numeric, data->numeric_count * sizeof(int32_t));
        descriptor->settings.numeric = (uintptr_t)source->numeric;
        descriptor->settings.numeric_count = data->numeric_count;
        descriptor->settings.numeric_capacity = data->numeric_count;
    }
    descriptor->settings.capacity = data->capacity;
    if (stream && stream->present) {
        if (szero_borrow_stream(stream, image_base, &source->stream)) {
            free(source);
            return SZERO_MATERIALIZE_INVALID;
        }
        descriptor->settings.stream = (uintptr_t)&source->stream;
    }
    /* Lists point to their sentinel, not to a fake full node at that address. */
    SzeroNativeMemberNode *sentinel = (SzeroNativeMemberNode *)&descriptor->members;
    descriptor->members.next = source->nodes;
    descriptor->members.previous = source->nodes + data->member_count - 1;
    descriptor->members.count = data->member_count;
    descriptor->member_count = (uint8_t)data->member_count;
    descriptor->field_e1 = data->field_e1;
    for (size_t i = 0; i < data->member_count; ++i) {
        const SzeroMemberData *input = data->members + i;
        SzeroNativeMemberNode *node = source->nodes + i;
        node->previous = i ? node - 1 : sentinel;
        node->next = i + 1 < data->member_count ? node + 1 : sentinel;
        make_string(source, &node->value.id, input->id);
        node->value.join_order = input->join_order;
        for (size_t j = 0; j < 2; ++j) {
            make_string(source, node->value.identity + j, input->identity[j]);
            if (input->owner)
                make_string(source, descriptor->owner_identity + j, input->identity[j]);
        }
        make_string(source, &node->value.address, input->address);
        node->value.field_88 = input->field_88;
        node->value.optional_present = input->optional_present;
        node->value.optional_value = input->optional_value;
        node->value.field_8b = input->field_8b;
        node->value.owner = input->owner;
    }
    SzeroNativeResult tagged = {0};
    tagged.tag = 2;
    tagged.payload[0] = (uintptr_t)descriptor;
    /* Verified original Win64 ABI; host supplies the exact-build factory.
     * Native allocation failure can be fatal. No claim of OOM recovery. */
    SzeroNativeResult *returned = factory(output, 0, &tagged);
    free(source);
    if (returned != output || output->tag != 2 ||
        !output->payload[0] || !output->payload[1])
        return SZERO_MATERIALIZE_NATIVE_RESULT;
    return SZERO_MATERIALIZED;
}

int szero_materialize_session(const SzeroSessionData *data,
    SzeroDescriptorFactory factory, SzeroNativeResult *output) {
    return materialize(data, NULL, 0, factory, output);
}

int szero_materialize_session_stream(const SzeroSessionData *data,
    const SzeroStreamWire *stream, uintptr_t image_base,
    SzeroDescriptorFactory factory, SzeroNativeResult *output) {
    if (!stream) return SZERO_MATERIALIZE_INVALID;
    return materialize(data, stream, image_base, factory, output);
}
