#include "native_bindings.h"
#include "native_lan_transport.h"
#include <stdio.h>
#include <string.h>

_Static_assert(sizeof(uintptr_t) == 8, "Exact supported target is Win64");
_Static_assert(sizeof(SzeroLanInlineString) == 32, "Native inline string");

static const uintptr_t channel_slots[12] = {
    0x5852a00,0x20f8b70,0x5852940,0x58522f0,0x56b4290,0x5877fb0,
    0x5877e30,0x587b220,0x587db90,0x587e630,0x58760c0,0x5875820
};

static int inspect(const SzeroLanTransportHost *h, uintptr_t *context,
    unsigned char *flag) {
    uintptr_t ctx, pointer, slots[12];
    uint32_t state, mode;
    unsigned char active, channel_state;
#define READ(addr, value) do { \
    if (!h->read(h->user,(addr),&(value),sizeof(value))) \
        return SZERO_LAN_TRANSPORT_READ_FAILED; \
} while (0)
    READ(h->image_base+szero_bind_rva(0x8cf84f8),ctx);
    if (!ctx || (ctx & 7) || ctx > UINTPTR_MAX-0x19d7)
        return SZERO_LAN_TRANSPORT_IDENTITY;
    READ(ctx,pointer);
    if (pointer != h->image_base+szero_bind_rva(0x7ba1bf8))
        return SZERO_LAN_TRANSPORT_IDENTITY;
    READ(ctx+0x40,pointer);
    if (pointer) return SZERO_LAN_TRANSPORT_BUSY;
    READ(ctx+0x19d6,active);
    READ(ctx+0x63c,state);
    if (active || state) return SZERO_LAN_TRANSPORT_BUSY;
    READ(ctx+0x65c,mode);
    if (mode != 2) return SZERO_LAN_TRANSPORT_MODE;
    READ(ctx+0x108,pointer);
    if (pointer != h->image_base+szero_bind_rva(0x7b8d640))
        return SZERO_LAN_TRANSPORT_IDENTITY;
    READ(pointer,slots);
    for (size_t i=0;i<12;++i)
        if (slots[i] != h->image_base+szero_bind_rva(channel_slots[i]))
            return SZERO_LAN_TRANSPORT_IDENTITY;
    /* Original channel+28 leaf145877fb0 reads channel+1b8 == ctx+2c0. */
    READ(ctx+0x2c0,channel_state);
    if (channel_state) return SZERO_LAN_TRANSPORT_BUSY;
    READ(ctx+0x661,*flag);
    if (*flag > 1) return SZERO_LAN_TRANSPORT_MODE;
    *context=ctx;
#undef READ
    return SZERO_LAN_TRANSPORT_OK;
}

int szero_lan_transport_prepare(const SzeroLanTransportHost *h,
    SzeroLanTransportReceipt *receipt) {
    uintptr_t context, context_again;
    unsigned char flag, flag_again;
    int code;
    if (!h || !receipt || receipt->valid || !h->read || !h->compare_byte ||
        !h->image_base || h->image_base > UINTPTR_MAX-szero_bind_rva(0x8cf84f8)-8)
        return SZERO_LAN_TRANSPORT_ARGUMENT;
    if (h->exact_image_verified != 1 || h->on_native_thread != 1)
        return SZERO_LAN_TRANSPORT_HOST_GATE;
    code=inspect(h,&context,&flag);
    if (code) return code;
    /* Recheck immediately before publication. Native-thread ownership is still
     * required; this double-read is not a global concurrency proof. */
    code=inspect(h,&context_again,&flag_again);
    if (code) return code;
    if (context_again != context || flag_again != flag)
        return SZERO_LAN_TRANSPORT_CHANGED;
    if (!h->compare_byte(h->user,context+0x661,flag,0))
        return SZERO_LAN_TRANSPORT_CHANGED;
    SzeroLanTransportReceipt ready={context,context+0x661,flag,flag!=0,1};
    *receipt=ready;
    return SZERO_LAN_TRANSPORT_OK;
}

int szero_lan_transport_bind_string(uint32_t port, SzeroLanInlineString *out) {
    SzeroLanInlineString result={{0}};
    char address[31];
    int length;
    if (!out || !port || port>65535) return SZERO_LAN_TRANSPORT_ARGUMENT;
    length=snprintf(address,sizeof(address),"127.0.0.1:%u",(unsigned)port);
    if (length<=0 || length>=31) return SZERO_LAN_TRANSPORT_ARGUMENT;
    result.bytes[0]=(unsigned char)((unsigned)length<<2);
    memcpy(result.bytes+1,address,(size_t)length+1);
    *out=result;
    return SZERO_LAN_TRANSPORT_OK;
}
