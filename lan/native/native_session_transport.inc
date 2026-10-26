/* Included only by the explicitly selected native session-v3 development
 * build. Never reinitialize an active native channel. This gate changes only
 * the recovered platform-transport override byte, not authentication/readiness.
 */
#include "native_lan_transport.h"

static SzeroLanTransportReceipt session_transport_receipts[4];
static unsigned session_transport_count;

static int session_transport_read(void *unused,uintptr_t address,void *out,size_t size) {
 (void)unused;return read_mem(address,out,size);
}
static int session_transport_compare(void *unused,uintptr_t address,
 unsigned char expected,unsigned char replacement) {
 (void)unused;MEMORY_BASIC_INFORMATION region;
 if(!VirtualQuery((const void *)address,&region,sizeof(region)) || region.State!=MEM_COMMIT ||
  (region.Protect&(PAGE_GUARD|PAGE_NOACCESS))) return 0;
 DWORD protection=region.Protect&0xff;
 if(protection!=PAGE_READWRITE && protection!=PAGE_WRITECOPY &&
    protection!=PAGE_EXECUTE_READWRITE && protection!=PAGE_EXECUTE_WRITECOPY) return 0;
 return __sync_val_compare_and_swap((volatile unsigned char *)address,
   expected,replacement)==expected;
}
static const char *session_transport_prepare(uintptr_t expected_context,uintptr_t expected_service) {
 uintptr_t ctx=0,service=0,vptr=0;
 if(GetCurrentThreadId()!=game_thread || InterlockedCompareExchange(&verification,0,0)!=2 ||
    !selected(&ctx,&service) || ctx!=expected_context || service!=expected_service ||
    !read_mem(service,&vptr,8) || !provider_owns(NULL,service,vptr))
  return "session_transport_host_gate";
 for(unsigned i=0;i<session_transport_count;i++) {
  SzeroLanTransportReceipt *receipt=&session_transport_receipts[i];
  if(receipt->context==ctx) {
   unsigned char flag=255;uint32_t mode=0;
   if(read_mem(ctx+0x661,&flag,1) && read_mem(ctx+0x65c,&mode,4) && flag==0 && mode==2)
    return NULL;
   /* A reused/reset context must pass the idle gate again. We retain the old
    * receipt, never use it to restore a potentially active context. */
  }
 }
 if(session_transport_count==4) return "session_transport_context_limit";
 SzeroLanTransportHost host={0};SzeroLanTransportReceipt receipt={0};
 host.read=session_transport_read;host.compare_byte=session_transport_compare;
 host.image_base=base;host.exact_image_verified=1;host.on_native_thread=1;
 int result=szero_lan_transport_prepare(&host,&receipt);
 static const char *const reasons[]={NULL,"session_transport_argument",
  "session_transport_host_gate","session_transport_unreadable","session_transport_identity",
  "session_transport_busy","session_transport_mode","session_transport_changed"};
 if(result!=SZERO_LAN_TRANSPORT_OK)
  return result>=0 && result<8?reasons[result]:"session_transport_invalid_result";
 session_transport_receipts[session_transport_count++]=receipt;
 return NULL;
}
