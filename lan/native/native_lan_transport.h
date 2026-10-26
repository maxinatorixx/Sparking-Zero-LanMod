/* SOURCE ONLY. No DLL export, hook installer or native initializer.
 * Hosts must verify the exact image SHA-256 and execute on the native game
 * thread before supplying these callbacks. A flag supplied by an untrusted
 * network peer is never evidence of image identity or thread ownership.
 */
#ifndef SZERO_NATIVE_LAN_TRANSPORT_H
#define SZERO_NATIVE_LAN_TRANSPORT_H
#include <stddef.h>
#include <stdint.h>

typedef int (*SzeroLanTransportRead)(void *user, uintptr_t address,
    void *output, size_t size);
/* Must compare the live byte with expected and write ONLY replacement when
 * equal. Return 1 only on success. This is not an unrestricted write callback.
 * The host owns synchronization; a successful byte CAS does not establish
 * global quiescence for the shared service or other native contexts.
 */
typedef int (*SzeroLanTransportCompareByte)(void *user, uintptr_t address,
    unsigned char expected, unsigned char replacement);
typedef struct {
    void *user;
    SzeroLanTransportRead read;
    SzeroLanTransportCompareByte compare_byte;
    uintptr_t image_base;
    unsigned char exact_image_verified, on_native_thread;
} SzeroLanTransportHost;
typedef struct {
    uintptr_t context, flag_address;
    unsigned char original_flag, changed, valid;
} SzeroLanTransportReceipt;
typedef struct { unsigned char bytes[32]; } SzeroLanInlineString;
enum {
    SZERO_LAN_TRANSPORT_OK = 0,
    SZERO_LAN_TRANSPORT_ARGUMENT = 1,
    SZERO_LAN_TRANSPORT_HOST_GATE = 2,
    SZERO_LAN_TRANSPORT_READ_FAILED = 3,
    SZERO_LAN_TRANSPORT_IDENTITY = 4,
    SZERO_LAN_TRANSPORT_BUSY = 5,
    SZERO_LAN_TRANSPORT_MODE = 6,
    SZERO_LAN_TRANSPORT_CHANGED = 7
};
extern const char szero_lan_transport_supported_sha256[];
/* Requires an empty receipt (valid==0). Rejects without changing it. Validates
 * title identity, original channel vtable/all12slots and native idle state,
 * preserves normalized mode2, then changes only context+661 from1 to0.
 * Native channel initialization remains with its original caller; no reinit.
 * The receipt records the old flag for a future explicitly guarded teardown;
 * this module NEVER automatically restores a potentially active context.
 */
int szero_lan_transport_prepare(const SzeroLanTransportHost *host,
    SzeroLanTransportReceipt *receipt);
/* Builds an owned inline native string in caller-provided UNOWNED storage;
 * do not pass an existing owned heap string. No native allocator is used.
 * Invalid ports leave output unchanged. Remote destination is separate.
 */
int szero_lan_transport_bind_string(uint32_t local_port,
    SzeroLanInlineString *output);
#endif
