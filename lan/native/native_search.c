/* Exact-build, opt-in native search/cancel handoff. NOT a playable LAN backend.
 * No auth/readiness replacement. Native query ownership remains with caller.
 * Hook yields through native scheduler; only worker performs socket I/O.
 * Game-thread polling writes changed-only bounded status, never in search hook.
 * Immutable service-instance vptr replacement is pinned for process lifetime.
 */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#include <ws2tcpip.h>
#include "native_image.h"
#include "native_bindings.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <stdarg.h>
#include <errno.h>
#include <stdlib.h>
static DWORD game_thread;
#ifdef SZERO_SESSION_V3
#include "native_session_host.h"
#include "native_session_codec.h"
#include "native_session_search.h"
#include "native_session_inspect.h"
#include "native_lan_identity.h"
#include "native_lan_userinfo.h"
#define SZERO_NATIVE_USERINFO_PROVIDER 1
static int session_v3;
#if defined(SZERO_NATIVE_SEARCH_TEST) || defined(SZERO_NATIVE_SESSION_IPC_TEST)
static int native_lan_profile; /* Legacy fixtures opt into HELLO4 explicitly. */
static int native_lan_multi;
#else
static int native_lan_profile=1;
static int native_lan_multi=1;
#endif
#define SZERO_PROXY_PORTS_MAX 64
static char native_lan_primary[39];
static volatile LONG native_lan_identity_state;
static unsigned native_lan_game_port,native_lan_proxy_port;
static unsigned native_lan_proxy_ports[SZERO_PROXY_PORTS_MAX],native_lan_proxy_count;
static volatile LONG provider_stopped;
static volatile LONG provider_hook_thread,provider_thread_mismatches;
enum { NATIVE_IDLE,NATIVE_THREAD_REFUSED,NATIVE_CAPTURE_REFUSED,NATIVE_WAITING,
 NATIVE_PREPARED,NATIVE_SERVER_COMMITTED,NATIVE_CACHED,NATIVE_SEARCH_RETURNED,
 NATIVE_FAILED,NATIVE_QUARANTINED,NATIVE_JOIN_FLAGS_REFUSED };
static volatile LONG provider_operation,provider_native_stage,provider_native_result;
/* Sticky search handoff fields survive the immediate subsequent create call,
 * which can otherwise hide a finite result between one-second Lua polls. */
static volatile LONG provider_search_request,provider_search_return_count=-1;
static volatile LONG provider_search_return_result=-1;
static volatile LONG provider_copy_mask=-1,provider_numeric_pass=-1;
static volatile LONG provider_self_exclusion=-1,provider_inspection_read;
static volatile LONG provider_join_attempts,provider_join_flags,provider_join_code=-1;
enum { CAPTURE_NONE,CAPTURE_IDENTITY,CAPTURE_SETTINGS_INVALID,CAPTURE_SETTINGS_UNREADABLE,
 CAPTURE_STREAM_UNSUPPORTED,CAPTURE_CAPACITY,CAPTURE_NUMERIC_LIMIT,CAPTURE_SERIALIZATION,
 CAPTURE_QUERY,CAPTURE_STATS };
static volatile LONG provider_capture_reason,provider_capture_code;
static SzeroStreamInfo provider_stream_info; /* Native-thread scalar metadata only. */
static const char *const capture_names[]={"none","identity_unavailable","settings_invalid",
 "settings_unreadable","stream_unsupported","member_capacity","numeric_limit",
 "serialization_failed","query_invalid","stats_unwritable"};
static int provider_capture_fail(LONG reason,LONG code) {
 InterlockedExchange(&provider_capture_reason,reason);
 InterlockedExchange(&provider_capture_code,code);return 0;
}
static const char *const native_stage_names[]={"idle","thread_refused","capture_refused","waiting",
 "prepared","server_committed","cached","search_returned","failed","quarantined","join_flags_refused"};
static void provider_telemetry(int kind,LONG stage,LONG result) {
 InterlockedExchange(&provider_operation,kind);InterlockedExchange(&provider_native_result,result);
 InterlockedExchange(&provider_native_stage,stage);
}
static int provider_native_thread(void) {
 DWORD observed=GetCurrentThreadId();
 InterlockedExchange(&provider_hook_thread,(LONG)observed);
 if(observed==game_thread) return 1;
 InterlockedIncrement(&provider_thread_mismatches);
 InterlockedExchange(&provider_native_stage,NATIVE_THREAD_REFUSED);return 0;
}
static void *session_operation(void *,void *,const void *,const void *,uint16_t,int);
static void process_session_job(void);
static void *session_bind(void *,void *);
static int provider_owns(void *,uintptr_t,uintptr_t);
static void *lifecycle_match(void *,void *,const void *,const void *,uint16_t);
static void *lifecycle_create(void *,void *,const void *,uint16_t);
static void *lifecycle_flags(void *,void *,const void *,uint16_t);
static void *lifecycle_leave(void *,void *,const void *);
static void *lifecycle_fence(void *,void *,const void *);
static void *lifecycle_settings(void *,void *,const void *,const void *);
static void *lifecycle_teardown(void *,void *);
static void *lifecycle_readiness(void *,void *);
static void *lifecycle_platform_operation(void *,void *,const void *,const void *);
static const char *session_transport_prepare(uintptr_t,uintptr_t);
static int lifecycle_wait_background(void *,void *,int);
static void lifecycle_tick(void *);
static int userinfo_service_ready(uintptr_t);
static void userinfo_clear(uintptr_t);
#endif

static uintptr_t base;
static volatile LONG verification, searches, cancels, creates, joins;
/* Scalar diagnostics only. Never write native pointers, identities or queries. */
enum { IPC_IDLE, IPC_ENDPOINT, IPC_SOCKET, IPC_CONNECT, IPC_HELLO,
 IPC_BEGIN, IPC_PENDING, IPC_CANCEL, IPC_CLOSED, IPC_FAILED };
enum { IPC_OK, IPC_ENDPOINT_MISSING, IPC_ENDPOINT_INVALID, IPC_SOCKET_ERROR,
 IPC_CONNECT_ERROR, IPC_HELLO_ERROR, IPC_BEGIN_ERROR, IPC_SERVER_REJECTED,
 IPC_PENDING_ERROR, IPC_TIMEOUT, IPC_QUERY_INVALID, IPC_CAPTURE_INVALID };
static volatile LONG ipc_phase, ipc_error, ipc_error_code, last_request;
static const char *const phase_names[]={"idle","endpoint","socket","connect","hello",
 "begin","pending","cancel","closed","failed"};
static const char *const error_names[]={"none","endpoint_missing","endpoint_invalid","socket_error",
 "connect_error","hello_error","begin_error","server_rejected","pending_error","search_timeout","query_invalid","native_input_refused"};
static void ipc_fail(LONG error,LONG code) {
 InterlockedExchange(&ipc_error_code,code);InterlockedExchange(&ipc_error,error);
 InterlockedExchange(&ipc_phase,IPC_FAILED);
}
static wchar_t endpoint[32768], report_path[32768];
static char instance[33];
static const uintptr_t tables[3]={0x7b95320,0x7b95400,0x7b954e0};
static const uintptr_t slots[3][28]={
 {0x58af630,0x20f8b70,0x58af360,0x58ae590,0x11072d0,0x59268f0,0x58ce9b0,0x58cec20,0x11072d0,0x58aeff0,0x5926200,0x58c8710,0x5925170,0x58c91a0,0x11072d0,0x58cdc30,0x58c8b70,0x5924640,0x59277a0,0x59269b0,0x58cac60,0x58c7e50,0x5928110,0x5929340,0x5926b10,0x5927dc0,0x5928330,0x5842490},
 {0x58af580,0x20f8b70,0x58af150,0x58ae180,0x10fdcc0,0x58c94d0,0x592f5f0,0x592f6f0,0x11072d0,0x592da10,0x592d050,0x592ccf0,0x592d000,0x592d720,0x10fdcc0,0x58cdc30,0x58c8b70,0x592c830,0x592ecc0,0x592db10,0x592e390,0x58c7e50,0x592f0b0,0x592fc30,0x592de30,0x592efa0,0x592f260,0x5842490},
 {0x58af540,0x20f8b70,0x58af080,0x58ae180,0x10fdcc0,0x58c94d0,0x592f5f0,0x592f6f0,0x10fdcc0,0x592da10,0x592d050,0x592ccf0,0x592d000,0x592d720,0x10fdcc0,0x58cdc30,0x58c8b70,0x592c830,0x592ecc0,0x592db10,0x592e390,0x58c7e50,0x592f0b0,0x592fc30,0x592de30,0x592efa0,0x592f260,0x5842490}
};
typedef struct {uintptr_t object,original,table[28];} Replacement;
static Replacement replacements[4];
static unsigned replacement_count;
#ifdef SZERO_SESSION_V3
#define NATIVE_IPC_MAX 16384
#else
#define NATIVE_IPC_MAX 8192
#endif
/* Single native search per process. Multiple separate game processes supported.
 * state: 0 free, -1 hook writing, 1 queued/pending, 2 worker error.
 * Worker may recycle ONLY after hook_done; never passes native pointers to IPC.
 */
static struct {volatile LONG state,cancel,hook_done; LONG id; char begin[NATIVE_IPC_MAX];} job;
#ifdef SZERO_SESSION_V3
static struct { char frame[SZERO_SESSION_FRAME_MAX]; int kind,empty;
 volatile LONG background;unsigned game_port,proxy_port; } session_job;
#endif
static volatile LONG sequence;
static void *(*current_task)(void);
static unsigned char (*yield_cancel)(void *);
static void *(*copy_error)(void *,const void *);

static int read_mem(uintptr_t p,void *out,SIZE_T size) {
 SIZE_T got=0;return p && ReadProcessMemory(GetCurrentProcess(),(void *)p,out,size,&got) && got==size;
}
static uint64_t qword(const void *p) {uint64_t x;memcpy(&x,p,8);return x;}
static uint32_t dword(const void *p) {uint32_t x;memcpy(&x,p,4);return x;}
static void *unavailable(void *out,int tagged) {
 memset(out,0,tagged?48:40);
 if(tagged) {*(uint32_t *)out=1;*(uint32_t *)((char *)out+8)=0x413;}
 else *(uint32_t *)out=0x413;
 return out;
}
static void *block_create(void *self,void *out,const void *settings,uint16_t flags) {
#ifdef SZERO_SESSION_V3
 if(session_v3) return lifecycle_create(self,out,settings,flags);
#endif
 (void)self;(void)settings;(void)flags;InterlockedIncrement(&creates);return unavailable(out,1);
}
#ifdef SZERO_SESSION_V3
static int join_flags_supported(uintptr_t service,uint32_t flags) {
 return flags==0 || flags==0x28 ||
  (flags==0x200 && native_lan_profile && userinfo_service_ready(service));
}
#endif
static void *block_join(void *self,void *out,const void *view,uint32_t flags) {
#ifdef SZERO_SESSION_V3
 if(session_v3) {
  InterlockedIncrement(&provider_join_attempts);
  InterlockedExchange(&provider_join_flags,(LONG)flags);
  InterlockedExchange(&provider_join_code,-1);
  /* Exact observed Quickmatch0x28: LOCAL14592db10 only tests bit7
   * (address suppression), while Steam1459269b0 never reads incoming flags.
   * Neither0x08 nor0x20 becomes a member/admission flag. Admit only the
   * observed equivalent value; unknown values, especially bit7, still refuse. */
  if(!join_flags_supported((uintptr_t)self,flags)) {
   InterlockedExchange(&provider_join_code,0x413);
   provider_telemetry(2,NATIVE_JOIN_FLAGS_REFUSED,1);return unavailable(out,0);
  }
  void *result=session_operation(self,out,view,NULL,0,2);
  InterlockedExchange(&provider_join_code,(LONG)dword(out));return result;
 }
#endif
 (void)self;(void)view;(void)flags;InterlockedIncrement(&joins);return unavailable(out,0);
}
static int append(char *dst,size_t *used,const char *fmt,...) {
 va_list args;va_start(args,fmt);int n=vsnprintf(dst+*used,NATIVE_IPC_MAX-*used,fmt,args);va_end(args);
 if(n<0 || (size_t)n>=NATIVE_IPC_MAX-*used) return 0;
 *used+=(size_t)n;return 1;
}
static int query_line(uintptr_t query,LONG id,char *line) {
 unsigned char q[0x50], filters[16*16], pairs[16*32];size_t used=0;
 if(!read_mem(query,q,sizeof(q))) return 0;
 uint64_t count=qword(q+0x10), cap=qword(q+0x18), compound=qword(q+0x30);
 if(count>16 || count>cap || compound>16 || compound>qword(q+0x38)) return 0;
 if(count && !read_mem(qword(q+8),filters,(SIZE_T)count*16)) return 0;
 if(compound && !read_mem(qword(q+0x28),pairs,(SIZE_T)compound*32)) return 0;
 if(!append(line,&used,"BEGIN2 %ld %lu %llu",id,(unsigned long)dword(q),(unsigned long long)count)) return 0;
 for(unsigned n=0;n<count;n++) {
  int32_t comparison,value;memcpy(&comparison,filters+n*16+8,4);memcpy(&value,filters+n*16+12,4);
  if(comparison<0 || comparison>4 || !append(line,&used," %llu %ld %ld",
   (unsigned long long)qword(filters+n*16),(long)comparison,(long)value)) return 0;
 }
 if(!append(line,&used," %llu",(unsigned long long)compound)) return 0;
 /* Native +28 is flat POD: AND across pairs, OR between each two predicates.
  * Copy both halves; the worker/server do not evaluate or discard constraints.
  */
 for(unsigned n=0;n<compound*2;n++) {
  int32_t comparison,value;memcpy(&comparison,pairs+n*16+8,4);memcpy(&value,pairs+n*16+12,4);
  if(comparison<0 || comparison>4 || !append(line,&used," %llu %ld %ld",
   (unsigned long long)qword(pairs+n*16),(long)comparison,(long)value)) return 0;
 }
 return append(line,&used," %lu %u %u %u\n",
  (unsigned long)dword(q+0x48),q[0x4c],q[0x4d],q[0x4e]);
}
static void *search(void *self,void *out,const void *query,void *stats) {
#ifdef SZERO_SESSION_V3
 if(session_v3) return session_operation(self,out,query,stats,0,3);
#endif
 (void)self;(void)stats;
 void *task=current_task();
 if(!task || InterlockedCompareExchange(&job.state,-1,0)!=0) return unavailable(out,1);
 LONG id=InterlockedIncrement(&sequence);
 if(id<=0 || !query_line((uintptr_t)query,id,job.begin)) {
  ipc_fail(IPC_QUERY_INVALID,0);
  InterlockedExchange(&job.state,0);return unavailable(out,1);
 }
 job.id=id;job.cancel=0;job.hook_done=0;InterlockedIncrement(&searches);
 InterlockedExchange(&job.state,1);
 ULONGLONG start=GetTickCount64();
 for(;;) {
  /* Real cooperative task yield. No Sleep/network/worker engine calls. */
  if(yield_cancel(task)) {
   InterlockedExchange(&job.cancel,1);InterlockedIncrement(&cancels);
   memset(out,0,48);copy_error((char *)out+8,(char *)task+0x58);*(uint32_t *)out=1;
   InterlockedExchange(&job.hook_done,1);return out;
  }
  if(InterlockedCompareExchange(&job.state,0,0)==2 || GetTickCount64()-start>120000) {
   if(InterlockedCompareExchange(&job.state,0,0)!=2) ipc_fail(IPC_TIMEOUT,0);
   InterlockedExchange(&job.cancel,1);unavailable(out,1);
   InterlockedExchange(&job.hook_done,1);return out;
  }
 }
}
static int writable_pointer(uintptr_t p) {
 MEMORY_BASIC_INFORMATION m;
 if((p&7) || !VirtualQuery((void *)p,&m,sizeof(m)) || m.State!=MEM_COMMIT ||
  (m.Protect&(PAGE_GUARD|PAGE_NOACCESS))) return 0;
 DWORD v=m.Protect&0xff;
 return (v==PAGE_READWRITE || v==PAGE_WRITECOPY || v==PAGE_EXECUTE_READWRITE || v==PAGE_EXECUTE_WRITECOPY) &&
  p+8<=(uintptr_t)m.BaseAddress+m.RegionSize;
}
static int selected(uintptr_t *ctx,uintptr_t *service) {
 uintptr_t vt,bundle;unsigned char selector;
 return read_mem(base+szero_bind_rva(0x8cf84f8),ctx,8) && read_mem(*ctx,&vt,8) && vt==base+szero_bind_rva(0x7ba1bf8) &&
  read_mem(*ctx+8,&bundle,8) && read_mem(*ctx+0x667,&selector,1) &&
  read_mem(bundle+(selector?0x50:0x48),service,8) && *service;
}
static const char *installed_reason(void) {
#ifdef SZERO_SESSION_V3
 if(session_v3) return "installed_session_v3_development";
#endif
 return "installed_search_cancel_only";
}
static const char *install(void) {
 uintptr_t ctx,service,vt,session,ctx2,service2;unsigned char active;
#ifdef SZERO_SESSION_V3
 if(session_v3 && InterlockedCompareExchange(&provider_stopped,0,0)) return "session_provider_quarantined";
#endif
 if(!selected(&ctx,&service)) return "context_not_ready";
 for(unsigned n=0;n<replacement_count;n++)
  if(service==replacements[n].object && read_mem(service,&vt,8) && vt==(uintptr_t)replacements[n].table) {
#ifdef SZERO_SESSION_V3
   if(session_v3) {const char *reason=session_transport_prepare(ctx,service);if(reason) return reason;}
#endif
   return installed_reason();
  }
 if(!read_mem(ctx+0x40,&session,8) || session || !read_mem(ctx+0x19d6,&active,1) || active)
  return "active_context_refused";
#ifdef SZERO_SESSION_V3
 if(session_v3) {
  uint64_t cached=0;
  if(!read_mem(service+0x200,&cached,8) || cached) return "existing_native_cache_refused";
 }
#endif
 if(replacement_count==4 || !writable_pointer(service) || !read_mem(service,&vt,8)) return "service_guard_failed";
 unsigned kind;for(kind=0;kind<3;kind++) if(vt==base+szero_bind_rva(tables[kind])) break;
 if(kind==3) return "unknown_service_vtable";
 uintptr_t original[28];
 if(!read_mem(vt,original,sizeof(original))) return "unreadable_vtable";
 for(unsigned n=0;n<28;n++) if(original[n]!=base+szero_bind_rva(slots[kind][n])) return "vtable_slot_mismatch";
 Replacement *r=&replacements[replacement_count];
 r->object=service;r->original=vt;memcpy(r->table,original,sizeof(original));
 r->table[17]=(uintptr_t)block_create;r->table[18]=(uintptr_t)search;r->table[19]=(uintptr_t)block_join;
#ifdef SZERO_SESSION_V3
 if(session_v3) {
  r->table[13]=(uintptr_t)session_bind;
  r->table[7]=(uintptr_t)lifecycle_tick;
  r->table[12]=(uintptr_t)lifecycle_teardown;
  r->table[20]=(uintptr_t)lifecycle_match;
  r->table[22]=(uintptr_t)lifecycle_flags;
  r->table[23]=(uintptr_t)lifecycle_settings;
  r->table[24]=(uintptr_t)lifecycle_leave;
  r->table[25]=kind==0?(uintptr_t)lifecycle_platform_operation:(uintptr_t)lifecycle_readiness;
  r->table[26]=(uintptr_t)lifecycle_fence;
 }
#endif
 if(!selected(&ctx2,&service2) || ctx2!=ctx || service2!=service) return "selection_changed";
 if((uintptr_t)InterlockedCompareExchangePointer((void *volatile *)service,r->table,(void *)vt)!=vt)
  return "publication_raced";
 /* Published tables are never overwritten, even if rollback raced destruction. */
 replacement_count++;
 if(!selected(&ctx2,&service2) || ctx2!=ctx || service2!=service) {
  if(writable_pointer(service))
   InterlockedCompareExchangePointer((void *volatile *)service,(void *)vt,r->table);
  return "selection_changed_after_publication";
 }
#ifdef SZERO_SESSION_V3
 if(session_v3) {
  const char *reason=session_transport_prepare(ctx,service);
  if(reason) {
   if(writable_pointer(service)) InterlockedCompareExchangePointer((void *volatile *)service,(void *)vt,r->table);
   return reason;
  }
 }
#endif
 return installed_reason();
}
static void report(const char *reason) {
 wchar_t logging[4];
 if(GetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",logging,4)!=1 || logging[0]!=L'1')return;
 static char previous[2049],line[2049];
 LONG phase=InterlockedCompareExchange(&ipc_phase,0,0),error=InterlockedCompareExchange(&ipc_error,0,0);
 const char *revision="native-search-v2";
 static char thread_fields[1536];thread_fields[0]=0;
 const char *create_label="blocked_creates",*join_label="blocked_joins",*error_label=error_names[error];
#ifdef SZERO_SESSION_V3
 if(session_v3) {
  revision="native-session-v3-development-modes4";create_label="create_calls";join_label="join_calls";
  if(error==IPC_TIMEOUT) error_label="operation_timeout";
  int field_written=snprintf(thread_fields,sizeof(thread_fields),",\"expected_native_thread\":%lu,\"observed_hook_thread\":%lu,\"thread_mismatches\":%ld,\"quarantined\":%s,\"native_operation\":%ld,\"native_stage\":\"%s\",\"native_result\":%ld,\"native_capture\":\"%s\",\"native_capture_code\":%ld,\"native_stream_layout\":%u,\"native_stream_refusal\":%u,\"native_stream_vtable_rva\":%u,\"native_stream_size\":%llu,\"native_stream_read_cursor\":%llu,\"native_stream_write_cursor\":%llu",
   (unsigned long)game_thread,(unsigned long)(DWORD)InterlockedCompareExchange(&provider_hook_thread,0,0),
   InterlockedCompareExchange(&provider_thread_mismatches,0,0),
   InterlockedCompareExchange(&provider_stopped,0,0)?"true":"false",
   InterlockedCompareExchange(&provider_operation,0,0),
   native_stage_names[InterlockedCompareExchange(&provider_native_stage,0,0)],
   InterlockedCompareExchange(&provider_native_result,0,0),
   capture_names[InterlockedCompareExchange(&provider_capture_reason,0,0)],
   InterlockedCompareExchange(&provider_capture_code,0,0),
   provider_stream_info.layout,provider_stream_info.refusal,provider_stream_info.vtable_rva,
   (unsigned long long)provider_stream_info.size,(unsigned long long)provider_stream_info.read_cursor,
   (unsigned long long)provider_stream_info.write_cursor);
  if(field_written<0 || (size_t)field_written>=sizeof(thread_fields)) return;
  uintptr_t ctx=0,service=0,vptr=0;uint64_t count=0;LONG context_count=-1,service_kind=0;
  if(verification==2 && selected(&ctx,&service) && read_mem(service,&vptr,8) &&
     provider_owns(NULL,service,vptr)) {
   if(read_mem(ctx+0x3b8,&count,8) && count<=64) context_count=(LONG)count;
   for(unsigned n=0;n<replacement_count;n++) if(replacements[n].object==service)
    for(unsigned k=0;k<3;k++) if(replacements[n].original==base+szero_bind_rva(tables[k])) service_kind=(LONG)k+1;
  }
  size_t used=strlen(thread_fields);
  field_written=snprintf(thread_fields+used,sizeof(thread_fields)-used,
   ",\"native_search_request\":%ld,\"native_search_return_count\":%ld,\"native_search_return_result\":%ld,\"native_context_search_count\":%ld,\"native_service_kind\":%ld",
   InterlockedCompareExchange(&provider_search_request,0,0),
   InterlockedCompareExchange(&provider_search_return_count,0,0),
   InterlockedCompareExchange(&provider_search_return_result,0,0),context_count,service_kind);
  if(field_written<0 || (size_t)field_written>=sizeof(thread_fields)-used) return;
  used=strlen(thread_fields);
  field_written=snprintf(thread_fields+used,sizeof(thread_fields)-used,
   ",\"native_lan_identity\":%s",native_lan_profile?"true":"false");
  if(field_written<0 || (size_t)field_written>=sizeof(thread_fields)-used) return;
  used=strlen(thread_fields);
  field_written=snprintf(thread_fields+used,sizeof(thread_fields)-used,
   ",\"native_copy_mask\":%ld,\"native_numeric_pass\":%ld,\"native_self_exclusion\":%ld,\"native_inspection_read\":%ld,\"native_join_attempts\":%ld,\"native_join_flags\":%lu,\"native_join_code\":%ld",
   InterlockedCompareExchange(&provider_copy_mask,0,0),
   InterlockedCompareExchange(&provider_numeric_pass,0,0),
   InterlockedCompareExchange(&provider_self_exclusion,0,0),
   InterlockedCompareExchange(&provider_inspection_read,0,0),
   InterlockedCompareExchange(&provider_join_attempts,0,0),
   (unsigned long)(DWORD)InterlockedCompareExchange(&provider_join_flags,0,0),
   InterlockedCompareExchange(&provider_join_code,0,0));
  if(field_written<0 || (size_t)field_written>=sizeof(thread_fields)-used) return;
 }
#endif
 int written=snprintf(line,sizeof(line),"{\"version\":1,\"revision\":\"%s\",\"status\":\"%s\",\"reason\":\"%s\",\"binding_error\":\"%s\",\"searches\":%ld,\"cancels\":%ld,\"%s\":%ld,\"%s\":%ld,\"ipc_phase\":\"%s\",\"ipc_error\":\"%s\",\"ipc_error_code\":%ld,\"last_request\":%ld%s}\n",
  revision,!strcmp(reason,installed_reason())?"installed":"waiting",reason,szero_bindings_error(),
  InterlockedCompareExchange(&searches,0,0),InterlockedCompareExchange(&cancels,0,0),
  create_label,InterlockedCompareExchange(&creates,0,0),join_label,InterlockedCompareExchange(&joins,0,0),
  phase_names[phase],error_label,InterlockedCompareExchange(&ipc_error_code,0,0),
  InterlockedCompareExchange(&last_request,0,0),thread_fields);
 if(written<0 || (size_t)written>=sizeof(line)) return; /* Never emit truncated JSON. */
 if(!strcmp(line,previous)) return;
 FILE *f=_wfopen(report_path,L"wb");if(!f) return;
 if(fputs(line,f)>=0 && !ferror(f)) strcpy(previous,line);
 fclose(f);
}
static int verify_image(void) {
#if defined(SZERO_NATIVE_SEARCH_TEST) || defined(SZERO_NATIVE_SESSION_IPC_TEST)
 return szero_native_image(base,0);
#else
 return szero_native_image(base,0) && szero_bindings_init(base);
#endif
}
static int wait_socket(SOCKET s,int writing,ULONGLONG deadline) {
 while(GetTickCount64()<deadline) {
  fd_set f;FD_ZERO(&f);FD_SET(s,&f);struct timeval t={0,50000};
  int r=select(0,writing?NULL:&f,writing?&f:NULL,NULL,&t);if(r) return r>0;
 }return 0;
}
static int send_line(SOCKET s,const char *p) {
 size_t size=strlen(p);ULONGLONG deadline=GetTickCount64()+5000;
 while(size) {if(!wait_socket(s,1,deadline)) return 0;int n=send(s,p,(int)size,0);
  if(n<=0) return 0;
  p+=n;size-=n;}return 1;
}
static int receive_line(SOCKET s,char *line,size_t size) {
 ULONGLONG deadline=GetTickCount64()+5000;size_t used=0;
 while(used+1<size) {if(!wait_socket(s,0,deadline)) return 0;
  int n=recv(s,line+used,1,0);if(n!=1) return 0;if(line[used++]=='\n') {line[used]=0;return 1;}}
 return 0;
}
#ifdef SZERO_SESSION_V3
static int greeting_uint(const char **cursor,unsigned *output) {
 const char *p=*cursor;unsigned value=0;
 if(*p<'1'||*p>'9')return 0;
 while(*p>='0'&&*p<='9') {
  value=value*10u+(unsigned)(*p++-'0');if(value>65535)return 0;
 }
 if(*p++!=' ')return 0;
 *output=value;*cursor=p;return 1;
}
static int session_greeting(const char *reply,unsigned *game_out,unsigned *proxy_out) {
 unsigned game=0,proxy=0;int end=0;char principal[39]={0};
 unsigned ports[SZERO_PROXY_PORTS_MAX]={0},count=0;
 int valid;
 if(native_lan_profile && native_lan_multi) {
  const char *cursor=reply;
  if(strncmp(cursor,"READY5 ",7))return 0;
  cursor+=7;
  if(!greeting_uint(&cursor,&game) || !greeting_uint(&cursor,&count) || count>SZERO_PROXY_PORTS_MAX)return 0;
  for(unsigned n=0;n<count;n++) {
   if(!greeting_uint(&cursor,ports+n) || ports[n]==game)return 0;
   for(unsigned j=0;j<n;j++)if(ports[j]==ports[n])return 0;
  }
  if(strlen(cursor)!=39 || cursor[38]!='\n')return 0;
  memcpy(principal,cursor,38);end=(int)(cursor-reply+38);proxy=ports[0];
  valid=szero_lan_identity_valid((const unsigned char *)principal,38);
 } else valid=native_lan_profile?
  sscanf(reply,"READY4 %u %u %38s%n",&game,&proxy,principal,&end)==3 &&
   szero_lan_identity_valid((const unsigned char *)principal,strlen(principal)):
  sscanf(reply,"READY3 %u %u%n",&game,&proxy,&end)==2;
 if(!valid || strcmp(reply+end,"\n") || !game || game>65535 || !proxy || proxy>65535 || game==proxy) return 0;
 /* Validate the COMPLETE response before publishing immutable process state. */
 if(native_lan_profile) {
  LONG state=InterlockedCompareExchange(&native_lan_identity_state,-1,0);
  if(state==0) {
   memcpy(native_lan_primary,principal,sizeof(principal));
   native_lan_game_port=game;native_lan_proxy_port=proxy;
   native_lan_proxy_count=count;
   memcpy(native_lan_proxy_ports,ports,sizeof(ports));
   InterlockedExchange(&native_lan_identity_state,1);
  } else if(state!=1 || memcmp(native_lan_primary,principal,sizeof(principal)) ||
    native_lan_game_port!=game || native_lan_proxy_port!=proxy || native_lan_proxy_count!=count ||
    memcmp(native_lan_proxy_ports,ports,sizeof(ports))) return 0;
 }
 *game_out=game;*proxy_out=proxy;return 1;
}
#endif
static SOCKET connect_bridge(void) {
 InterlockedExchange(&ipc_phase,IPC_ENDPOINT);
 FILE *f=_wfopen(endpoint,L"rb");char raw[160],magic[40],token[33],port_text[6];unsigned port=0;int used=0,ok=0;
 if(!f) {ipc_fail(IPC_ENDPOINT_MISSING,errno);return INVALID_SOCKET;}
 size_t got=fread(raw,1,sizeof(raw)-1,f);raw[got]=0;
 int tail=fgetc(f),read_error=ferror(f);fclose(f);
 /* MinGW's scanf can return0 rather thanEOF after consuming final whitespace.
  * Do not use a second fscanf(" %c")==EOF as a validity check. Bound the file,
  * parse actual ASCII digits, then explicitly check every trailing byte.
  */
 if(!read_error && tail==EOF && !memchr(raw,0,got) &&
  sscanf(raw,"%39s %5[0-9] %32[0-9a-f]%n",magic,port_text,token,&used)==3 &&
  !strcmp(magic,"SZERO_NATIVE_ENDPOINT_V1") && !strcmp(token,instance)) {
  ok=1;for(size_t n=(size_t)used;n<got;n++)
   if(raw[n]!=' ' && raw[n]!='\t' && raw[n]!='\r' && raw[n]!='\n') ok=0;
  port=(unsigned)strtoul(port_text,NULL,10);if(!port || port>65535) ok=0;
 }
 if(!ok) {ipc_fail(IPC_ENDPOINT_INVALID,0);return INVALID_SOCKET;}
 InterlockedExchange(&ipc_phase,IPC_SOCKET);
 SOCKET s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
 if(s==INVALID_SOCKET) {ipc_fail(IPC_SOCKET_ERROR,WSAGetLastError());return s;}
 u_long nonblock=1;if(ioctlsocket(s,FIONBIO,&nonblock)) {ipc_fail(IPC_SOCKET_ERROR,WSAGetLastError());goto fail;}
 struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_port=htons((u_short)port);a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 InterlockedExchange(&ipc_phase,IPC_CONNECT);
 int r=connect(s,(struct sockaddr *)&a,sizeof(a));
 if(r==SOCKET_ERROR && WSAGetLastError()!=WSAEWOULDBLOCK) {ipc_fail(IPC_CONNECT_ERROR,WSAGetLastError());goto fail;}
 if(!wait_socket(s,1,GetTickCount64()+5000)) {ipc_fail(IPC_CONNECT_ERROR,WSAETIMEDOUT);goto fail;}
 int error=0,len=sizeof(error);
 if(getsockopt(s,SOL_SOCKET,SO_ERROR,(char *)&error,&len) || error) {
  ipc_fail(IPC_CONNECT_ERROR,error?error:WSAGetLastError());goto fail;
 }
 InterlockedExchange(&ipc_phase,IPC_HELLO);
 char line[128],reply[512];snprintf(line,sizeof(line),"HELLO %s\n",instance);
#ifdef SZERO_SESSION_V3
 if(session_v3) snprintf(line,sizeof(line),"%s %s\n",native_lan_profile?(native_lan_multi?"HELLO5":"HELLO4"):"HELLO3",instance);
#endif
 int greeting=send_line(s,line) && receive_line(s,reply,sizeof(reply));
#ifdef SZERO_SESSION_V3
 if(session_v3) {
  unsigned game=0,proxy=0;
  greeting=greeting && session_greeting(reply,&game,&proxy);
  if(greeting) { session_job.game_port=game;session_job.proxy_port=proxy; }
 } else
#endif
 greeting=greeting && !strcmp(reply,"READY\n");
 if(!greeting) {
  ipc_fail(IPC_HELLO_ERROR,WSAGetLastError());goto fail;
 }
 return s;
fail:closesocket(s);return INVALID_SOCKET;
}
#ifdef SZERO_SESSION_V3
#include "native_session_provider.inc"
#include "native_session_lifecycle.inc"
#include "native_session_transport.inc"
#endif
/* Same production request lifecycle can be exercised by standalone IPC fixture;
 * it has no hash bypass and is not exported from the distributed DLL. */
static void process_job(void) {
  InterlockedExchange(&last_request,job.id);InterlockedExchange(&ipc_error,IPC_OK);
  InterlockedExchange(&ipc_error_code,0);
  SOCKET s=connect_bridge();char line[128],expected[128];
  snprintf(expected,sizeof(expected),"PENDING %ld\n",job.id);
  if(s==INVALID_SOCKET) InterlockedExchange(&job.state,2);
  else {
   InterlockedExchange(&ipc_phase,IPC_BEGIN);
   if(!send_line(s,job.begin) || !receive_line(s,line,sizeof(line))) {
    ipc_fail(IPC_BEGIN_ERROR,WSAGetLastError());InterlockedExchange(&job.state,2);
   } else if(strcmp(line,expected)) {
    ipc_fail(IPC_SERVER_REJECTED,0);InterlockedExchange(&job.state,2);
   } else InterlockedExchange(&ipc_phase,IPC_PENDING);
  }
  while(InterlockedCompareExchange(&job.state,0,0)==1 && !InterlockedCompareExchange(&job.cancel,0,0)) {
   fd_set f;FD_ZERO(&f);FD_SET(s,&f);struct timeval t={0,50000};int r=select(0,&f,NULL,NULL,&t);
   if(r<0 || (r>0 && (!receive_line(s,line,sizeof(line)) || strcmp(line,expected)))) {
    ipc_fail(IPC_PENDING_ERROR,WSAGetLastError());InterlockedExchange(&job.state,2);
   }
  }
  if(s!=INVALID_SOCKET) {
   if(InterlockedCompareExchange(&ipc_error,0,0)==IPC_OK) InterlockedExchange(&ipc_phase,IPC_CANCEL);
   snprintf(line,sizeof(line),"CANCEL %ld\n",job.id);send_line(s,line);closesocket(s);
  }
  while(!InterlockedCompareExchange(&job.hook_done,0,0)) Sleep(20);
  InterlockedExchange(&job.state,0);
  if(InterlockedCompareExchange(&ipc_error,0,0)==IPC_OK) InterlockedExchange(&ipc_phase,IPC_CLOSED);
}
static DWORD WINAPI worker(void *unused) {
 (void)unused;
 if(!verify_image()) {InterlockedExchange(&verification,3);return 0;}
 current_task=(void *(*)(void))(base+szero_bind_rva(0x5817fe0));
 yield_cancel=(unsigned char (*)(void *))(base+szero_bind_rva(0x5818a50));
 copy_error=(void *(*)(void *,const void *))(base+szero_bind_rva(0x2804ac0));
 WSADATA w;if(WSAStartup(MAKEWORD(2,2),&w)) {InterlockedExchange(&verification,3);return 0;}
#ifdef SZERO_SESSION_V3
 if(session_v3) {
  SOCKET bootstrap=INVALID_SOCKET;ULONGLONG deadline=GetTickCount64()+15000;
  do {
   bootstrap=connect_bridge();
   if(bootstrap!=INVALID_SOCKET) break;
   Sleep(100);
  } while(GetTickCount64()<deadline);
  if(bootstrap==INVALID_SOCKET) {InterlockedExchange(&verification,3);return 0;}
  closesocket(bootstrap);
  InterlockedExchange(&ipc_error,IPC_OK);InterlockedExchange(&ipc_error_code,0);
  InterlockedExchange(&ipc_phase,IPC_IDLE);
 }
#endif
 InterlockedExchange(&verification,2);
 for(;;) {
  if(InterlockedCompareExchange(&job.state,0,0)!=1) {Sleep(20);continue;}
#ifdef SZERO_SESSION_V3
  if(session_v3) { process_session_job();continue; }
#endif
  process_job();
 }
}
__declspec(dllexport) int szero_native_search(void *lua) {
 (void)lua;
 if(!verification) {
  wchar_t enabled[4],id[40];HMODULE own;wchar_t *slash;
  if(GetEnvironmentVariableW(L"SZERO_LAN_NATIVE_SEARCH",enabled,4)!=1 || enabled[0]!=L'1' ||
   GetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",id,40)!=32) return 0;
  for(unsigned n=0;n<32;n++) {if(!((id[n]>=L'a'&&id[n]<=L'f')||(id[n]>=L'0'&&id[n]<=L'9'))) return 0;instance[n]=(char)id[n];}
  /* Pin forever before publishing callbacks; no unload/reinitialization support. */
  if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
   (const wchar_t *)(uintptr_t)&szero_native_search,&own) || !GetModuleFileNameW(own,endpoint,32768)) return 0;
  slash=wcsrchr(endpoint,L'\\');if(!slash || slash-endpoint>32400) return 0;
  swprintf(slash+1,200,L"lan_runtime_%ls.native.endpoint",id);
  wcscpy(report_path,endpoint);slash=wcsrchr(report_path,L'\\');swprintf(slash+1,200,L"native_search_%ls.json",id);
  base=(uintptr_t)GetModuleHandleW(NULL);game_thread=GetCurrentThreadId();
#ifdef SZERO_SESSION_V3
  /* Explicit developer opt-in only. Never inferred from native_search=true. */
  wchar_t experimental[4];
  session_v3=GetEnvironmentVariableW(L"SZERO_LAN_NATIVE_SESSION3",experimental,4)==1 && experimental[0]==L'1';
#endif
  InterlockedExchange(&verification,1);HANDLE h=CreateThread(NULL,0,worker,NULL,0,NULL);
  if(h) CloseHandle(h);else InterlockedExchange(&verification,3);
 }
 if(GetCurrentThreadId()!=game_thread) return 0;
 LONG v=InterlockedCompareExchange(&verification,0,0);
 report(v==2?install():v==3?"verification_or_network_initialization_failed":"validating_image");return 0;
}

#ifdef SZERO_NATIVE_SEARCH_TEST
/* Standalone synthetic fixture. No game image is loaded or executed. */
#include <assert.h>
static unsigned char fixture_task[0x100], fixture_query[0x50], fixture_filters[256];
static int fixture_yields, fixture_copies, fixture_cancel_at, fixture_worker_error;
static DWORD fixture_thread;
static void *fixture_current(void) { return fixture_task; }
static void *fixture_no_task(void) { return NULL; }
static unsigned char fixture_yield(void *task) {
 assert(task==fixture_task && GetCurrentThreadId()==fixture_thread);
 assert(job.state==1 && !job.hook_done);
 fixture_yields++;
 if(fixture_worker_error) {InterlockedExchange(&job.state,2);return 0;}
 return fixture_yields>=fixture_cancel_at;
}
static void *fixture_copy(void *dst,const void *src) {
 assert(src==fixture_task+0x58 && GetCurrentThreadId()==fixture_thread);
 fixture_copies++;memcpy(dst,src,40);return dst;
}
static void fixture_put64(void *dst,uint64_t value) {memcpy(dst,&value,8);}
static void fixture_put32(void *dst,uint32_t value) {memcpy(dst,&value,4);}
static void fixture_reset(void) {
 memset(replacements,0,sizeof(replacements));replacement_count=0;
 memset(&job,0,sizeof(job));sequence=searches=cancels=creates=joins=0;
 memset(fixture_query,0,sizeof(fixture_query));memset(fixture_filters,0,sizeof(fixture_filters));
 memset(fixture_task,0,sizeof(fixture_task));fixture_yields=fixture_copies=0;
 fixture_cancel_at=3;fixture_worker_error=0;fixture_thread=GetCurrentThreadId();
 current_task=fixture_current;yield_cancel=fixture_yield;copy_error=fixture_copy;
#ifdef SZERO_SESSION_V3
 session_v3=0;provider_stopped=0;session_transport_count=0;
 memset(session_transport_receipts,0,sizeof(session_transport_receipts));
 memset(provider_applied_frames,0,sizeof(provider_applied_frames));
 memset(userinfo_replacements,0,sizeof(userinfo_replacements));userinfo_replacement_count=0;
 memset(&session_job,0,sizeof(session_job));game_thread=fixture_thread;
#endif
}
static void fixture_install_setup(unsigned kind) {
 uintptr_t ctx=base+0x1000,bundle=base+0x4000,service=base+0x5000;
 fixture_put64((void *)(base+szero_bind_rva(0x8cf84f8)),ctx);
 memset((void *)ctx,0,0x2000);memset((void *)bundle,0,0x100);memset((void *)service,0,0x300);
 fixture_put64((void *)ctx,base+szero_bind_rva(0x7ba1bf8));fixture_put64((void *)(ctx+8),bundle);
 fixture_put64((void *)(bundle+0x48),service);fixture_put64((void *)(bundle+0x50),service);
 fixture_put64((void *)service,base+szero_bind_rva(tables[kind]));
 for(unsigned n=0;n<28;n++) fixture_put64((void *)(base+szero_bind_rva(tables[kind])+8*n),base+szero_bind_rva(slots[kind][n]));
}
static void fixture_canary(const unsigned char *p,size_t begin,size_t end) {
 for(size_t n=begin;n<end;n++) assert(p[n]==0xa5);
}
static void fixture_errors(void) {
 unsigned char out[80],borrowed[80],original[80];memset(borrowed,0x6b,sizeof(borrowed));memcpy(original,borrowed,sizeof(original));
 memset(out,0xa5,sizeof(out));assert(block_create(NULL,out+8,borrowed,0x4321)==out+8);
 fixture_canary(out,0,8);fixture_canary(out,56,80);
 assert(dword(out+8)==1 && dword(out+16)==0x413);
 for(unsigned n=20;n<56;n++) assert(!out[n]);
 memset(out,0xa5,sizeof(out));assert(block_join(NULL,out+8,borrowed,0x12345678)==out+8);
 fixture_canary(out,0,8);fixture_canary(out,48,80);
 assert(dword(out+8)==0x413);for(unsigned n=12;n<48;n++) assert(!out[n]);
 assert(!memcmp(original,borrowed,sizeof(original)) && creates==1 && joins==1);
}
static void fixture_queries(void) {
 char line[NATIVE_IPC_MAX];unsigned char snapshot[0x50],pairs[16*32]={0};
 assert(query_line((uintptr_t)fixture_query,7,line));assert(!strcmp(line,"BEGIN2 7 0 0 0 0 0 0 0\n"));
 fixture_put32(fixture_query,123);fixture_put64(fixture_query+8,(uintptr_t)fixture_filters);
 fixture_put64(fixture_query+0x10,16);fixture_put64(fixture_query+0x18,16);
 for(unsigned n=0;n<16;n++) {
  fixture_put64(fixture_filters+16*n,0xffffffffffffffffULL-n);
  fixture_put32(fixture_filters+16*n+8,n%5);fixture_put32(fixture_filters+16*n+12,0x80000000U+n);
 }
 fixture_put32(fixture_query+0x48,3);fixture_query[0x4c]=2;fixture_query[0x4d]=4;fixture_query[0x4e]=6;
 memcpy(snapshot,fixture_query,sizeof(snapshot));assert(query_line((uintptr_t)fixture_query,8,line));
 assert(strstr(line,"18446744073709551615 0 -2147483648") && strstr(line," 0 3 2 4 6\n"));
 assert(!memcmp(snapshot,fixture_query,sizeof(snapshot)));
 fixture_put64(fixture_query+0x10,17);assert(!query_line((uintptr_t)fixture_query,1,line));
 fixture_put64(fixture_query+0x10,16);fixture_put64(fixture_query+0x18,15);assert(!query_line((uintptr_t)fixture_query,1,line));
 fixture_put64(fixture_query+0x18,16);fixture_put32(fixture_filters+8,5);assert(!query_line((uintptr_t)fixture_query,1,line));
 fixture_put32(fixture_filters+8,0xffffffffU);assert(!query_line((uintptr_t)fixture_query,1,line));
 fixture_put32(fixture_filters+8,0);fixture_put64(fixture_query+0x30,17);assert(!query_line((uintptr_t)fixture_query,1,line));
 fixture_put64(fixture_query+0x30,1);fixture_put64(fixture_query+0x38,0);assert(!query_line((uintptr_t)fixture_query,1,line));
 assert(!query_line(1,1,line));fixture_put64(fixture_query+0x30,0);fixture_put64(fixture_query+8,1);
 assert(!query_line((uintptr_t)fixture_query,1,line));
 /* Both halves of every OR-pair are copied, with signed values and uint64 keys.
  * Verify the largest accepted vector and preserve all borrowed bytes. */
 fixture_put64(fixture_query+8,(uintptr_t)fixture_filters);
 fixture_put64(fixture_query+0x28,(uintptr_t)pairs);
 fixture_put64(fixture_query+0x30,16);fixture_put64(fixture_query+0x38,16);
 for(unsigned n=0;n<32;n++) {
  fixture_put64(pairs+16*n,0xffffffffffffffffULL-n);
  fixture_put32(pairs+16*n+8,n%5);fixture_put32(pairs+16*n+12,0x80000000U+n);
 }
 memcpy(snapshot,fixture_query,sizeof(snapshot));
 assert(query_line((uintptr_t)fixture_query,9,line));assert(strlen(line)<NATIVE_IPC_MAX);
 assert(strstr(line," 16 18446744073709551615 0 -2147483648 18446744073709551614 1 -2147483647"));
 assert(!memcmp(snapshot,fixture_query,sizeof(snapshot)));
 fixture_put32(pairs+16+8,5);assert(!query_line((uintptr_t)fixture_query,9,line));
 fixture_put32(pairs+16+8,1);fixture_put64(fixture_query+0x28,1);
 assert(!query_line((uintptr_t)fixture_query,9,line));
}
static void fixture_install_guards(void) {
 uintptr_t ctx=base+0x1000,service=base+0x5000;
 for(unsigned kind=0;kind<3;kind++) {
  fixture_reset();fixture_install_setup(kind);
  assert(!strcmp(install(),"installed_search_cancel_only") && replacement_count==1);
  assert(qword((void *)service)==(uintptr_t)replacements[0].table);
  for(unsigned n=0;n<28;n++) {
   uintptr_t expected=n==17?(uintptr_t)block_create:n==18?(uintptr_t)search:n==19?(uintptr_t)block_join:base+szero_bind_rva(slots[kind][n]);
   assert(replacements[0].table[n]==expected);
  }
  assert(!strcmp(install(),"installed_search_cancel_only") && replacement_count==1);
 }
 fixture_reset();fixture_install_setup(0);fixture_put64((void *)(ctx+0x40),1);
 assert(!strcmp(install(),"active_context_refused"));fixture_put64((void *)(ctx+0x40),0);
 *(unsigned char *)(ctx+0x19d6)=1;assert(!strcmp(install(),"active_context_refused"));*(unsigned char *)(ctx+0x19d6)=0;
 fixture_put64((void *)(base+szero_bind_rva(tables[0])+8*27),1);assert(!strcmp(install(),"vtable_slot_mismatch"));
 fixture_install_setup(0);fixture_put64((void *)service,base+0x1110);assert(!strcmp(install(),"unknown_service_vtable"));
 fixture_install_setup(0);replacement_count=4;assert(!strcmp(install(),"service_guard_failed"));replacement_count=0;
 fixture_put64((void *)ctx,0);assert(!strcmp(install(),"context_not_ready"));
 fixture_install_setup(0);*(unsigned char *)(ctx+0x667)=1;
 assert(!strcmp(install(),"installed_search_cancel_only"));
 assert(!writable_pointer(service+1) && !writable_pointer(1));
 DWORD previous;assert(VirtualProtect((void *)service,4096,PAGE_READONLY,&previous));
 assert(!writable_pointer(service));assert(VirtualProtect((void *)service,4096,previous,&previous));
 /* Actual interlocked publish already tested; deterministic competing mutation
  * between selected() and CAS requires instrumentation, not this fixture. */
}
static void fixture_searches(void) {
 unsigned char out[80],snapshot[0x50],stats[32];
 fixture_reset();memcpy(snapshot,fixture_query,sizeof(snapshot));memset(stats,0x7c,sizeof(stats));
 fixture_put32(fixture_task+0x58,0x123400); /* legitimate synthetic cancelled error */
 memset(out,0xa5,sizeof(out));assert(search(NULL,out+8,fixture_query,stats)==out+8);
 assert(fixture_yields==3 && fixture_copies==1 && searches==1 && cancels==1);
 assert(dword(out+8)==1 && !memcmp(out+16,fixture_task+0x58,40));
 fixture_canary(out,0,8);fixture_canary(out,56,80);
 assert(job.state==1 && job.cancel && job.hook_done && !strcmp(job.begin,"BEGIN2 1 0 0 0 0 0 0 0\n"));
 assert(!memcmp(snapshot,fixture_query,sizeof(snapshot)));for(unsigned n=0;n<sizeof(stats);n++) assert(stats[n]==0x7c);
 /* Late worker ownership prevents a second hook from reusing pending storage. */
 assert(search(NULL,out+8,fixture_query,stats)==out+8 && dword(out+16)==0x413 && searches==1);
 fixture_reset();fixture_worker_error=1;search(NULL,out+8,fixture_query,stats);
 assert(fixture_yields==1 && !fixture_copies && job.cancel && job.hook_done && dword(out+16)==0x413);
 fixture_reset();current_task=fixture_no_task;search(NULL,out+8,fixture_query,stats);
 assert(!fixture_yields && !searches && !job.state && dword(out+16)==0x413);
 fixture_reset();search(NULL,out+8,(void *)1,stats);assert(!job.state && !searches && !fixture_yields);
 fixture_reset();job.state=-1;search(NULL,out+8,fixture_query,stats);assert(job.state==-1 && !searches);
}
#ifdef SZERO_SESSION_V3
static void fixture_session_capture(void) {
 fixture_reset();session_job.game_port=32111;
 uintptr_t service=base+0x5000,bundle=base+0x6000,user=base+0x8000;
 fixture_put64((void *)(service+8),bundle);fixture_put64((void *)(bundle+0x18),user);
 memset((void *)(user+0x200),0,0x40);
 *(unsigned char *)(user+0x200)=3<<2;memcpy((void *)(user+0x201),"abc",3);
 *(unsigned char *)(user+0x220)=3<<2;memcpy((void *)(user+0x221),"def",3);
 SzeroNativeSettings settings={0},before;settings.capacity=2;before=settings;
 assert(provider_request(service,&settings,NULL,3,1,1));
 assert(strstr(job.begin,"CREATE3 1 ") && strstr(job.begin," 616263 646566 "));
 assert(!provider_capture_reason && !memcmp(&before,&settings,sizeof(settings)));
 settings.capacity=3;
 assert(!provider_request(service,&settings,NULL,3,1,2) && provider_capture_reason==CAPTURE_CAPACITY && provider_capture_code==3);
 settings.capacity=2;settings.numeric_count=settings.numeric_capacity=1;settings.numeric=1;
 before=settings;
 assert(!provider_request(service,&settings,NULL,3,1,3) && provider_capture_reason==CAPTURE_SETTINGS_UNREADABLE);
 assert(!memcmp(&before,&settings,sizeof(settings)));
 settings.numeric_count=settings.numeric_capacity=settings.numeric=0;
 uintptr_t stream[9]={0};settings.stream=(uintptr_t)stream;
 assert(!provider_request(service,&settings,NULL,3,1,4) && provider_capture_reason==CAPTURE_STREAM_UNSUPPORTED);
 settings.stream=0;fixture_put64((void *)(bundle+0x18),1);
 assert(!provider_request(service,&settings,NULL,3,1,5) && provider_capture_reason==CAPTURE_IDENTITY);
 fixture_put64((void *)(bundle+0x18),user);
 assert(provider_request(service,&settings,NULL,3,1,6) && !provider_capture_reason);
}
static void fixture_session_install_setup(unsigned kind) {
 static const uintptr_t channel[12]={0x5852a00,0x20f8b70,0x5852940,0x58522f0,
  0x56b4290,0x5877fb0,0x5877e30,0x587b220,0x587db90,0x587e630,0x58760c0,0x5875820};
 fixture_reset();fixture_install_setup(kind);session_v3=1;verification=2;
 session_job.game_port=32111;session_job.proxy_port=32112;
 uintptr_t ctx=base+0x1000;
 fixture_put32((void *)(ctx+0x65c),2);*(unsigned char *)(ctx+0x661)=1;
 fixture_put64((void *)(ctx+0x108),base+szero_bind_rva(0x7b8d640));
 for(unsigned i=0;i<12;i++) fixture_put64((void *)(base+szero_bind_rva(0x7b8d640)+8*i),base+channel[i]);
}
static void fixture_session_install(void) {
 uintptr_t ctx=base+0x1000,service=base+0x5000;
 fixture_reset();
 assert(!provider_frame_same(1,"snapshot-a\n"));
 assert(provider_frame_mark(1,"snapshot-a\n") && provider_frame_same(1,"snapshot-a\n"));
 assert(!provider_frame_same(2,"snapshot-a\n") && !provider_frame_same(1,"snapshot-b\n"));
 assert(provider_frame_mark(1,"snapshot-b\n") && provider_frame_same(1,"snapshot-b\n"));
 assert(provider_frame_mark(2,"snapshot-a\n") && provider_frame_mark(3,"snapshot-a\n") &&
  provider_frame_mark(4,"snapshot-a\n") && !provider_frame_mark(5,"snapshot-a\n"));
 provider_frame_clear(1);assert(!provider_frame_same(1,"snapshot-b\n"));
 assert(provider_frame_same(2,"snapshot-a\n") && provider_frame_mark(5,"snapshot-a\n"));
 fixture_reset();
 unsigned char stats[64];memset(stats,0x6b,sizeof(stats));uint64_t counts[2]={16,9};
 assert(provider_stats_writable(NULL) && provider_stats_writable(stats+8));
 assert(!provider_stats_writable((void *)1));
 provider_stats_complete(stats+8,counts,1);
 assert(stats[8]==1 && qword(stats+16)==16 && qword(stats+24)==9);
 for(unsigned i=0;i<8;i++) assert(stats[i]==0x6b);
 for(unsigned i=9;i<16;i++) assert(stats[i]==0x6b);
 for(unsigned i=32;i<64;i++) assert(stats[i]==0x6b);
 DWORD protection;
 assert(VirtualProtect((void *)(base+0x7000),4096,PAGE_READONLY,&protection));
 assert(!provider_stats_writable((void *)(base+0x7000)));
 assert(VirtualProtect((void *)(base+0x7000),4096,protection,&protection));
 for(unsigned kind=0;kind<3;kind++) {
  fixture_session_install_setup(kind);
  assert(!strcmp(install(),"installed_session_v3_development"));
  assert(replacement_count==1 && session_transport_count==1);
  assert(!*(unsigned char *)(ctx+0x661));
  Replacement *r=&replacements[0];
  for(unsigned i=0;i<28;i++) {
   uintptr_t expected=base+szero_bind_rva(slots[kind][i]);
   switch(i) {
    case 7:expected=(uintptr_t)lifecycle_tick;break;
    case 12:expected=(uintptr_t)lifecycle_teardown;break;
    case 13:expected=(uintptr_t)session_bind;break;
    case 17:expected=(uintptr_t)block_create;break;
    case 18:expected=(uintptr_t)search;break;
    case 19:expected=(uintptr_t)block_join;break;
    case 20:expected=(uintptr_t)lifecycle_match;break;
    case 22:expected=(uintptr_t)lifecycle_flags;break;
    case 23:expected=(uintptr_t)lifecycle_settings;break;
    case 24:expected=(uintptr_t)lifecycle_leave;break;
    case 25:expected=kind==0?(uintptr_t)lifecycle_platform_operation:(uintptr_t)lifecycle_readiness;break;
    case 26:expected=(uintptr_t)lifecycle_fence;break;
   }
   assert(r->table[i]==expected);
  }
  unsigned normalize=99;assert(provider_default_normalize(service,&normalize) && normalize==(kind==2));
  assert(provider_request(service,fixture_query,NULL,0,3,71));
  assert(strncmp(job.begin,kind==2?"SEARCH3 71 1 ":"SEARCH3 71 0 ",13)==0);
  fixture_put64((void *)(r->original+0x40),base+1);
  assert(!provider_default_normalize(service,&normalize));
  fixture_put64((void *)(r->original+0x40),base+szero_bind_rva(slots[kind][8]));
  assert(qword((void *)service)==(uintptr_t)r->table);
  assert(!strcmp(install(),"installed_session_v3_development") && session_transport_count==1);
 }
 /* Post-publication transport rejection rolls vptr back without changing661;
  * immutable published table remains retained rather than reused/freed. */
 fixture_session_install_setup(0);*(unsigned char *)(ctx+0x2c0)=1;
 assert(!strcmp(install(),"session_transport_busy") && replacement_count==1);
 assert(qword((void *)service)==base+szero_bind_rva(tables[0]) && *(unsigned char *)(ctx+0x661)==1);
 assert(!session_transport_count);
 fixture_session_install_setup(0);fixture_put64((void *)(base+szero_bind_rva(0x7b8d640)+8*11),base+1);
 assert(!strcmp(install(),"session_transport_identity"));
 assert(qword((void *)service)==base+szero_bind_rva(tables[0]) && *(unsigned char *)(ctx+0x661)==1);
 fixture_session_install_setup(0);fixture_put32((void *)(ctx+0x65c),1);
 assert(!strcmp(install(),"session_transport_mode"));
 assert(qword((void *)service)==base+szero_bind_rva(tables[0]) && *(unsigned char *)(ctx+0x661)==1);
 fixture_session_install_setup(0);verification=1;
 assert(!strcmp(install(),"session_transport_host_gate"));
 assert(qword((void *)service)==base+szero_bind_rva(tables[0]) && *(unsigned char *)(ctx+0x661)==1);
 fixture_session_install_setup(0);provider_stopped=1;
 assert(!strcmp(install(),"session_provider_quarantined") && !replacement_count);
 assert(qword((void *)service)==base+szero_bind_rva(tables[0]) && *(unsigned char *)(ctx+0x661)==1);
 fixture_session_install_setup(0);fixture_put64((void *)(service+0x200),1);
 assert(!strcmp(install(),"existing_native_cache_refused") && !replacement_count);
 assert(qword((void *)service)==base+szero_bind_rva(tables[0]) && *(unsigned char *)(ctx+0x661)==1);
 fixture_reset();
}
static void fixture_userinfo_publication(void) {
 fixture_session_install_setup(0);
 assert(!strcmp(install(),"installed_session_v3_development"));
 native_lan_profile=1;native_lan_identity_state=1;
 memcpy(native_lan_primary,"szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",39);
 uintptr_t service=base+0x5000,user=base+0x8000,bundle=base+0x4000;
 fixture_put64((void *)(service+8),bundle);
 memset((void *)user,0x67,0x378);fixture_put64((void *)(bundle+0x18),user);
 fixture_put64((void *)user,base+szero_bind_rva(0x7b94d68));
 for(unsigned i=0;i<20;i++) fixture_put64((void *)(base+szero_bind_rva(0x7b94d68)+8*i),base+szero_bind_rva(userinfo_steam_slots[i]));
 fixture_put64((void *)(base+szero_bind_rva(0x7b94d68)+8*19),base+1);
 assert(!userinfo_publish(service) && !userinfo_replacement_count);
 fixture_put64((void *)(base+szero_bind_rva(0x7b94d68)+8*19),base+szero_bind_rva(userinfo_steam_slots[19]));
 unsigned char identity_before[64];memcpy(identity_before,(void *)(user+0x200),64);
 SzeroSessionCodec codec={0};codec.data.member_count=1;
 const unsigned char remote[]="szlan:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
 codec.members[0].identity[0]=(SzeroText){remote,38};
 userinfo_observe(service,&codec);
 assert(userinfo_replacement_count==1 && userinfo_service_ready(service));
 assert(join_flags_supported(service,0x200));
 assert(join_flags_supported(service,0) && join_flags_supported(service,0x28));
 assert(!join_flags_supported(service,0x228) && !join_flags_supported(service,0x280));
 UserInfoReplacement *r=userinfo_binding(user);assert(r);
 for(unsigned i=0;i<20;i++) assert(r->table[i]==(i==19?(uintptr_t)userinfo_hook:base+szero_bind_rva(userinfo_steam_slots[i])));
 assert(!memcmp(identity_before,(void *)(user+0x200),64));
 assert(userinfo_publish(service)==r && userinfo_replacement_count==1);
 SzeroNativeString id={0};id.words[0]=1;id.words[1]=(uintptr_t)remote;id.words[2]=id.words[3]=38;
 SzeroUserInfoRecord row={0};row.id=id;row.flags=255;
 SzeroUserInfoVector ids={(uintptr_t)&id,1,1},rows={(uintptr_t)&row,1,1};
 unsigned char guarded[64];memset(guarded,0xa5,sizeof(guarded));
 assert(userinfo_hook((void *)user,guarded+8,&ids,&rows)==guarded+8);
 assert(dword(guarded+8)==2 && !rows.data && row.flags==0);
 fixture_canary(guarded,0,8);fixture_canary(guarded,56,64);
 /* The synthetic original function addresses are not executable: succeeding
  * above proves the actual callback did not delegate a LAN ID there. */
 const unsigned char foreign[]="szlan:cccccccccccccccccccccccccccccccc";
 id.words[1]=(uintptr_t)foreign;row.id=id;rows=(SzeroUserInfoVector){(uintptr_t)&row,1,1};
 memset(guarded,0xa5,sizeof(guarded));userinfo_hook((void *)user,guarded+8,&ids,&rows);
 assert(dword(guarded+8)==1 && dword(guarded+16)==0x413 && rows.data==(uintptr_t)&row);
 fixture_canary(guarded,0,8);fixture_canary(guarded,56,64);
 userinfo_clear(service);assert(!userinfo_service_ready(service));
 assert(!join_flags_supported(service,0x200));
 native_lan_profile=0;native_lan_identity_state=0;fixture_reset();
}
static void fixture_session_report(void) {
 fixture_session_install_setup(2);
 assert(!strcmp(install(),"installed_session_v3_development"));
 searches=cancels=creates=joins=sequence=2147483647;
 provider_search_request=2147483647;provider_search_return_count=1;provider_search_return_result=0;
 provider_copy_mask=127;provider_numeric_pass=provider_self_exclusion=provider_inspection_read=1;
 provider_join_attempts=2147483647;provider_join_flags=(LONG)UINT32_MAX;provider_join_code=2147483647;
 game_thread=UINT32_MAX;provider_hook_thread=(LONG)UINT32_MAX;
 provider_thread_mismatches=provider_operation=2147483647;provider_native_result=provider_capture_code=INT32_MIN;
 provider_native_stage=NATIVE_JOIN_FLAGS_REFUSED;provider_capture_reason=CAPTURE_SETTINGS_UNREADABLE;
 provider_stream_info.layout=provider_stream_info.refusal=UINT32_MAX;
 provider_stream_info.size=provider_stream_info.read_cursor=provider_stream_info.write_cursor=UINT64_MAX;
 provider_stream_info.vtable_rva=UINT32_MAX;
 wchar_t temporary[MAX_PATH];
 assert(GetTempPathW(MAX_PATH,temporary) && GetTempFileNameW(temporary,L"szr",0,report_path));
 report(installed_reason());
 FILE *file=_wfopen(report_path,L"rb");assert(file);
 char contents[2050];size_t size=fread(contents,1,sizeof(contents)-1,file);fclose(file);contents[size]=0;
 assert(size && size<=2048 && contents[size-1]=='\n' && contents[size-2]=='}');
 assert(strstr(contents,"\"revision\":\"native-session-v3-development-modes4\""));
 assert(strstr(contents,"\"native_search_request\":2147483647"));
 assert(strstr(contents,"\"native_search_return_count\":1"));
 assert(strstr(contents,"\"native_service_kind\":3"));
 assert(strstr(contents,"\"native_copy_mask\":127"));
 assert(strstr(contents,"\"native_join_flags\":4294967295"));
 assert(strstr(contents,"\"native_join_code\":2147483647"));
 /* Early unsupported flags remain refused and sticky, even though the
  * accepted-operation counter never increments. Borrowed view is unread. */
 unsigned char output[56];memset(output,0xa5,sizeof(output));
 LONG before=joins;
 const uint32_t refused_flags[]={0x08,0x20,0x29,0x80,0x128,0x200,0x201,0x228,0x280,UINT32_MAX};
 for(unsigned n=0;n<sizeof(refused_flags)/sizeof(refused_flags[0]);n++) {
  memset(output,0xa5,sizeof(output));provider_join_attempts=0;
  block_join(NULL,output+8,NULL,refused_flags[n]);
  assert(provider_join_attempts==1 && joins==before && provider_join_code==0x413);
  assert((DWORD)provider_join_flags==refused_flags[n] && dword(output+8)==0x413);
  for(unsigned i=0;i<8;i++) assert(output[i]==0xa5);
  for(unsigned i=48;i<56;i++) assert(output[i]==0xa5);
 }
 assert(DeleteFileW(report_path));report_path[0]=0;fixture_reset();
}
#endif
int main(void) {
 base=(uintptr_t)VirtualAlloc(NULL,0x9000000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(base);
 fixture_reset();fixture_errors();fixture_queries();fixture_install_guards();fixture_searches();
#ifdef SZERO_SESSION_V3
 native_lan_profile=1;
 unsigned game=42,proxy=43;
 const char *bad_greetings[]={"UNAVAILABLE4\n",
  "READY4 0 123 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY4 123 123 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY4 123 124 szlan:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n",
  "READY4 123 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa extra\n",
  "READY4 123 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"};
 for(unsigned i=0;i<sizeof(bad_greetings)/sizeof(bad_greetings[0]);i++) {
  assert(!session_greeting(bad_greetings[i],&game,&proxy));
  assert(native_lan_identity_state==0 && game==42 && proxy==43);
 }
 assert(session_greeting("READY4 123 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",&game,&proxy));
 assert(game==123 && proxy==124 && native_lan_identity_state==1);
 assert(session_greeting("READY4 123 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",&game,&proxy));
 assert(!session_greeting("READY4 125 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",&game,&proxy));
 assert(!session_greeting("READY4 123 124 szlan:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\n",&game,&proxy));
 assert(game==123 && proxy==124 && native_lan_primary[6]=='a');
 native_lan_multi=1;native_lan_identity_state=0;game=42;proxy=43;
 const char *bad_multi[]={"READY4 123 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY5 123 0 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY5 123 65 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY5 123 2 124 124 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY5 123 2 124 123 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY5 123 2 124 00125 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",
  "READY5 123 2 124 125 szlan:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n",
  "READY5 123 2 124 125 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa extra\n"};
 for(unsigned i=0;i<sizeof(bad_multi)/sizeof(bad_multi[0]);i++) {
  assert(!session_greeting(bad_multi[i],&game,&proxy));
  assert(native_lan_identity_state==0 && game==42 && proxy==43);
 }
 assert(session_greeting("READY5 123 3 124 125 126 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",&game,&proxy));
 assert(native_lan_proxy_count==3 && native_lan_proxy_ports[2]==126 && game==123 && proxy==124);
 assert(!session_greeting("READY5 123 3 124 125 127 szlan:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n",&game,&proxy));
 unsigned port=0;
 assert(provider_proxy_port((SzeroText){(const unsigned char *)"127.0.0.1:125",13},&port) && port==125);
 assert(!provider_proxy_port((SzeroText){(const unsigned char *)"127.0.0.1:127",13},&port));
 assert(!provider_proxy_port((SzeroText){(const unsigned char *)"127.0.0.1:0125",14},&port));
 assert(!provider_proxy_port((SzeroText){(const unsigned char *)"192.168.1.1:125",15},&port));
 native_lan_multi=0;native_lan_proxy_count=0;memset(native_lan_proxy_ports,0,sizeof(native_lan_proxy_ports));
 native_lan_profile=0;native_lan_identity_state=0;
 memset(native_lan_primary,0,sizeof(native_lan_primary));
 native_lan_game_port=native_lan_proxy_port=0;
 fixture_session_capture();
 fixture_session_install();
 fixture_userinfo_publication();
 fixture_session_report();
#endif
 assert(VirtualFree((void *)base,0,MEM_RELEASE));puts("native_search synthetic Win64 contracts passed");return 0;
}
#endif
