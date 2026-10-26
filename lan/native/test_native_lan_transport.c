#include "native_lan_transport.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

#define BASE ((uintptr_t)0x140000000)
#define CONTEXT ((uintptr_t)0x50000000)
typedef struct {
    unsigned char context[0x1a00];
    uintptr_t global, slots[12];
    uintptr_t fail_address;
    unsigned reads, writes;
    int compare_fail, switch_context;
} Fixture;
static const uintptr_t slots[12]={
    0x5852a00,0x20f8b70,0x5852940,0x58522f0,0x56b4290,0x5877fb0,
    0x5877e30,0x587b220,0x587db90,0x587e630,0x58760c0,0x5875820
};
static void ptr(Fixture *f,size_t at,uintptr_t value) {
    memcpy(f->context+at,&value,8);
}
static int read_memory(void *user,uintptr_t address,void *out,size_t size) {
    Fixture *f=user;
    ++f->reads;
    if (address==f->fail_address) return 0;
    if (address==BASE+0x8cf84f8 && size==8) {
        if(f->switch_context && f->reads>1) {
            uintptr_t moved=CONTEXT+8; memcpy(out,&moved,8);
        } else memcpy(out,&f->global,8);
        return 1;
    }
    if(address==BASE+0x7b8d640 && size==sizeof(f->slots)) {
        memcpy(out,f->slots,size); return 1;
    }
    if(address>=CONTEXT && address-CONTEXT<=sizeof(f->context) &&
        size<=sizeof(f->context)-(address-CONTEXT)) {
        memcpy(out,f->context+address-CONTEXT,size); return 1;
    }
    return 0;
}
static int compare_byte(void *user,uintptr_t address,unsigned char expected,
    unsigned char replacement) {
    Fixture *f=user;
    assert(address==CONTEXT+0x661 && replacement==0);
    ++f->writes;
    if(f->compare_fail || f->context[0x661]!=expected) return 0;
    f->context[0x661]=replacement; return 1;
}
static SzeroLanTransportHost reset(Fixture *f) {
    memset(f,0,sizeof(*f)); f->global=CONTEXT;
    ptr(f,0,BASE+0x7ba1bf8); ptr(f,0x108,BASE+0x7b8d640);
    f->context[0x65c]=2; f->context[0x661]=1;
    for(size_t i=0;i<12;++i) f->slots[i]=BASE+slots[i];
    SzeroLanTransportHost h={f,read_memory,compare_byte,BASE,1,1}; return h;
}
static void rejected(SzeroLanTransportHost *h,int expected) {
    Fixture *f=h->user;
    SzeroLanTransportReceipt receipt={0},before=receipt;
    unsigned char memory[sizeof(f->context)]; memcpy(memory,f->context,sizeof(memory));
    assert(szero_lan_transport_prepare(h,&receipt)==expected);
    assert(!memcmp(&receipt,&before,sizeof(receipt)));
    assert(!memcmp(memory,f->context,sizeof(memory)));
    assert(f->writes==0);
}
int main(void) {
    Fixture f; SzeroLanTransportHost h; SzeroLanTransportReceipt r={0};
    h=reset(&f);
    unsigned char original[sizeof(f.context)]; memcpy(original,f.context,sizeof(original));
    assert(!szero_lan_transport_prepare(&h,&r));
    assert(r.valid && r.changed && r.original_flag==1 && r.context==CONTEXT);
    assert(r.flag_address==CONTEXT+0x661 && f.writes==1 && f.context[0x661]==0);
    original[0x661]=0; assert(!memcmp(original,f.context,sizeof(original)));
    assert(szero_lan_transport_prepare(&h,&r)==SZERO_LAN_TRANSPORT_ARGUMENT);
    r.valid=0; h=reset(&f); f.context[0x661]=0;
    assert(!szero_lan_transport_prepare(&h,&r));
    assert(r.valid && !r.changed && !r.original_flag);
    h=reset(&f); h.exact_image_verified=0; rejected(&h,SZERO_LAN_TRANSPORT_HOST_GATE);
    h=reset(&f); h.on_native_thread=0; rejected(&h,SZERO_LAN_TRANSPORT_HOST_GATE);
    h=reset(&f); f.global=0; rejected(&h,SZERO_LAN_TRANSPORT_IDENTITY);
    h=reset(&f); f.global=CONTEXT+1; rejected(&h,SZERO_LAN_TRANSPORT_IDENTITY);
    h=reset(&f); ptr(&f,0,BASE+0x7ba1bf0); rejected(&h,SZERO_LAN_TRANSPORT_IDENTITY);
    h=reset(&f); ptr(&f,0x40,1); rejected(&h,SZERO_LAN_TRANSPORT_BUSY);
    h=reset(&f); f.context[0x19d6]=1; rejected(&h,SZERO_LAN_TRANSPORT_BUSY);
    h=reset(&f); f.context[0x63c]=1; rejected(&h,SZERO_LAN_TRANSPORT_BUSY);
    h=reset(&f); f.context[0x65c]=4; rejected(&h,SZERO_LAN_TRANSPORT_MODE);
    h=reset(&f); ptr(&f,0x108,BASE+0x7b8d648); rejected(&h,SZERO_LAN_TRANSPORT_IDENTITY);
    for(size_t i=0;i<12;++i) {
        h=reset(&f); f.slots[i]^=8; rejected(&h,SZERO_LAN_TRANSPORT_IDENTITY);
    }
    h=reset(&f); f.context[0x2c0]=4; rejected(&h,SZERO_LAN_TRANSPORT_BUSY);
    h=reset(&f); f.context[0x661]=2; rejected(&h,SZERO_LAN_TRANSPORT_MODE);
    const uintptr_t reads[]={BASE+0x8cf84f8,CONTEXT,CONTEXT+0x40,
        CONTEXT+0x19d6,CONTEXT+0x63c,CONTEXT+0x65c,CONTEXT+0x108,
        BASE+0x7b8d640,CONTEXT+0x2c0,CONTEXT+0x661};
    for(size_t i=0;i<sizeof(reads)/sizeof(reads[0]);++i) {
        h=reset(&f); f.fail_address=reads[i]; rejected(&h,SZERO_LAN_TRANSPORT_READ_FAILED);
    }
    h=reset(&f); f.compare_fail=1; memset(&r,0,sizeof(r));
    assert(szero_lan_transport_prepare(&h,&r)==SZERO_LAN_TRANSPORT_CHANGED);
    assert(!r.valid && f.context[0x661]==1 && f.writes==1);
    h=reset(&f); f.switch_context=1; rejected(&h,SZERO_LAN_TRANSPORT_IDENTITY);
    h=reset(&f); h.image_base=UINTPTR_MAX-0x100; rejected(&h,SZERO_LAN_TRANSPORT_ARGUMENT);
    struct { unsigned char before[8]; SzeroLanInlineString value; unsigned char after[8]; } guarded;
    memset(&guarded,0xa5,sizeof(guarded));
    assert(szero_lan_transport_bind_string(0,&guarded.value)==SZERO_LAN_TRANSPORT_ARGUMENT);
    assert(szero_lan_transport_bind_string(65536,&guarded.value)==SZERO_LAN_TRANSPORT_ARGUMENT);
    for(size_t i=0;i<sizeof(guarded);++i) assert(((unsigned char*)&guarded)[i]==0xa5);
    const uint32_t ports[]={1,33001,65535};
    for(size_t i=0;i<3;++i) {
        assert(!szero_lan_transport_bind_string(ports[i],&guarded.value));
        char address[31]; int length=snprintf(address,sizeof(address),"127.0.0.1:%u",ports[i]);
        assert(guarded.value.bytes[0]==(unsigned char)(length<<2));
        assert(!memcmp(guarded.value.bytes+1,address,(size_t)length+1));
        for(size_t j=(size_t)length+2;j<32;++j) assert(!guarded.value.bytes[j]);
        for(size_t j=0;j<8;++j) assert(guarded.before[j]==0xa5 && guarded.after[j]==0xa5);
    }
    assert(szero_lan_transport_bind_string(1,NULL)==SZERO_LAN_TRANSPORT_ARGUMENT);
    puts("native LAN transport contracts passed (synthetic memory only)");
    return 0;
}
