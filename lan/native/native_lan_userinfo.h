/* Scoped LAN relationship metadata. Never an account/authentication provider. */
#ifndef SZERO_NATIVE_LAN_USERINFO_H
#define SZERO_NATIVE_LAN_USERINFO_H
#include "session_materializer.h"
#define SZERO_USERINFO_MAX_IDS 1024
typedef struct {uintptr_t data;uint64_t count,capacity;} SzeroUserInfoVector;
typedef struct {SzeroNativeString id;unsigned char flags,padding[7];} SzeroUserInfoRecord;
typedef struct {
    void *context;
    int (*read)(void *,uintptr_t,void *,size_t);
    int (*writable)(void *,uintptr_t,size_t);
    /* Validated exclusively-owned native ranges must remain stable until
     * return; write cannot fail after writable succeeds. */
    void (*write)(void *,uintptr_t,const void *,size_t);
    int (*ready)(void *);
    int (*known)(void *,const unsigned char principal[38]);
    /* Mixed requests deep-copy real strings with their NATIVE allocator.
     * The original method can consume/reorder/destroy individual IDs. */
    int (*copy_id)(void *,SzeroNativeString *,const SzeroNativeString *);
    void (*destroy_id)(void *,SzeroNativeString *);
    void *(*original)(void *,void *,void *,const void *,void *);
} SzeroUserInfoCallbacks;
enum { SZERO_USERINFO_REFUSED=0,SZERO_USERINFO_DELEGATED=1,SZERO_USERINFO_LAN=2 };
/* Actual user+98 ABI: borrowed vector of32B native IDs, consumed vector of40B
 * ID+flag records, tagged48B result (success owns a three-word vector at+8).
 * Real IDs always use original callback; canonical known LAN IDs never do.
 * Unknown/malformed namespace IDs, borrowed unreadability or ownership guard
 * failures refuse before mutations. All-LAN calls move existing native storage;
 * mixed calls use audited native copy/destroy callbacks for real-ID copies.
 */
int szero_lan_userinfo_dispatch(void *self,void *out,const void *ids,void *records,
    const SzeroUserInfoCallbacks *callbacks);
#endif
