/* Opt-in exact-build observer. Private, statically linked MinHook; temporary
 * IN-MEMORY entry hooks only, NEVER disk patches. All native arguments/RAX
 * forwarded unchanged. Read-only outputs; no account/ticket/string logging.
 * Trampolines and DLL stay process-pinned for suspended native fibers.
 * Only the known game thread records; worker owns hashing, hooks and file I/O.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
#include <io.h>
#include "vendor/minhook/include/MinHook.h"
enum {LIMIT=512,HOOKS=18};
enum {OFF,VERIFYING,ARMED,STOPPING,STOPPED,FAILED};
#ifdef SZERO_SERVICE_TRACE_TEST
#define TRACE_MS 1200u
#define WAIT_MS 2400u
#else
#define TRACE_MS 300000u
#define WAIT_MS 1800000u
#endif
typedef struct {SYSTEMTIME time;uint32_t id,parent,mask,code,tag,backend_status;int slot,kind,readable,code_valid,category,origin,backend_status_valid,native_result,native_result_valid;} Event;
typedef struct {uint32_t id,parent,mask,backend_status;int slot,origin,backend_status_valid;} Token;
typedef void *(*Fn2)(uintptr_t,uintptr_t);
typedef void *(*Fn4)(uintptr_t,uintptr_t,uintptr_t,uintptr_t);
typedef void *(*Fn3)(uintptr_t,uintptr_t,uintptr_t);
typedef void *(*Fn6)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t);
typedef void *(*Fn7)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t);
typedef void *(*Fn8)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t);
typedef void *(*Fn9)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t);
static Fn6 original_check,original_login;static Fn4 original_platform;static Fn9 original_maintenance;
static Fn4 original_provider;static Fn8 original_backend;static Fn3 original_response;
static Fn7 original_http;static Fn4 original_error_string;static Fn2 original_error_copy;
static Fn7 original_connect;static Fn4 original_peer_prepare;
static Fn4 original_member,original_peer_start;
static Fn2 original_wait,original_wait_result,original_commit,original_battle_result;
static Event ring[LIMIT];static volatile LONG state=OFF,written,inflight;
static unsigned consumed,serial,current_root;
static unsigned active_hooks=HOOKS;static DWORD game_thread;static ULONGLONG deadline;
static ULONGLONG idle_deadline;
static volatile LONG postpair_extension;
static volatile LONG64 postpair_deadline;
static unsigned postpair_depth;
static uintptr_t entries[HOOKS],image_base;static unsigned char installed_prefix[HOOKS][16];
static wchar_t log_path[32768],endpoint_path[32768];
static const char *names[HOOKS]={"online_check","platform_check","service_login","maintenance",
 "login_provider","backend_login","login_response","steam_http_exchange","http_failure_marker","http_error_copy",
 "post_pair_connect","post_pair_prepare","post_pair_member","post_pair_wait",
 "post_pair_wait_result","post_pair_commit","post_pair_peer_start","set_battle_result"};
#ifdef SZERO_SERVICE_TRACE_TEST
static const char *test_exports[HOOKS]={"trace_check","trace_platform","trace_login","trace_maintenance",
 "trace_provider","trace_backend","trace_response","trace_http","trace_error_string","trace_error_copy",
 "trace_connect","trace_peer_prepare","trace_member","trace_wait",
 "trace_wait_result","trace_commit","trace_peer_start","trace_battle_result"};
static int test_origin;
#endif
static const uintptr_t offsets[HOOKS]={0x5a7e7c0,0x58b1e90,0x5ad9740,0x5ada640,
 0x58f19f0,0x5ad9b00,0x5ad0d20,0x591cb70,0x5851440,0x5811d40,0x59aecb0,0x59bd290,
 0x59c9fd0,0x5985340,0x59acbf0,0x5993410,0x59b86c0,0x23d76a0};
static const unsigned char prefixes[HOOKS][16]={
 {0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x8d,0xac,0x24},
 {0x40,0x55,0x53,0x56,0x57,0x41,0x54,0x41,0x56,0x41,0x57,0x48,0x8d,0x6c,0x24,0x80},
 {0x40,0x53,0x48,0x81,0xec,0x80,0x00,0x00,0x00,0x48,0x8b,0x05,0xc0,0xe1,0x21,0x03},
 {0x40,0x55,0x53,0x56,0x57,0x41,0x55,0x41,0x56,0x48,0x8d,0xac,0x24,0x88,0xfc,0xff},
 {0x40,0x53,0x57,0x48,0x83,0xec,0x28,0x48,0x8b,0x01,0x49,0x8b,0xf8,0x48,0x8b,0xda},
 {0x40,0x55,0x53,0x56,0x57,0x41,0x54,0x41,0x56,0x41,0x57,0x48,0x8d,0xac,0x24,0xb0},
 {0x40,0x55,0x56,0x41,0x57,0x48,0x8d,0xac,0x24,0x90,0xfd,0xff,0xff,0x48,0x81,0xec},
 {0x48,0x89,0x5c,0x24,0x20,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57},
 {0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x6c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57},
 {0x40,0x53,0x48,0x83,0xec,0x50,0x4c,0x8b,0x42,0x08,0x48,0x8b,0xd9,0x8b,0x02,0x4c},
 {0x48,0x89,0x5c,0x24,0x20,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57},
 {0x40,0x55,0x53,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x8d,0x6c},
 {0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x7c,0x24,0x10,0x55,0x48,0x8d,0xac,0x24,0xf0},
 {0x48,0x89,0x5c,0x24,0x18,0x48,0x89,0x7c,0x24,0x20,0x55,0x48,0x8d,0x6c,0x24,0xa9},
 {0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x6c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57},
 {0x48,0x89,0x5c,0x24,0x18,0x55,0x48,0x8d,0x6c,0x24,0xa9,0x48,0x81,0xec,0xc0,0x00},
 {0x40,0x55,0x53,0x48,0x8d,0x6c,0x24,0xb1,0x48,0x81,0xec,0xc8,0x00,0x00,0x00,0x48},
 {0x48,0x89,0x5c,0x24,0x10,0x57,0x48,0x83,0xec,0x50,0x0f,0x10,0x81,0x60,0x13,0x00}};
/* Exact ORIGINAL call-return RVAs, independently checked as E8 instructions.
 * These classify a branch, not a ticket, address, packet or inferred exception. */
static int failure_origin(uintptr_t caller,int slot) {
 if(caller<image_base) return 0;
 uintptr_t rva=caller-image_base;
 if(slot==8) switch(rva) {
  case 0x591ccde:return 1; /* request handle zero */
  case 0x591d089:return 2; /* request header setter false */
  case 0x591d25e:return 3; /* raw POST body setter false */
  case 0x591e0be:return 4; /* unsupported method */
 }
 if(slot==9) switch(rva) {
  case 0x591d4d5:return 5; /* certificate requirement setter false */
  case 0x591d677:return 6; /* absolute timeout setter false */
  case 0x591d83c:return 7; /* send request false */
  case 0x591d989:return 8; /* send returned zero async call */
  case 0x591dba4:return 9; /* async holder has error status, not necessarily remote */
  case 0x591de47:return 10; /* native request holder missing or ID mismatched */
  case 0x591dfa4:return 11; /* native operation cancelled */
 }
 return 0;
}
static const char *origins[]={"none","create_request","set_header","set_raw_body",
 "unsupported_method","set_certificate_requirement","set_absolute_timeout","send_request",
 "zero_async_call","async_holder_error","missing_or_mismatched_request_holder","operation_cancelled"};
static const uintptr_t origin_returns[11]={0x591ccde,0x591d089,0x591d25e,0x591e0be,
 0x591d4d5,0x591d677,0x591d83c,0x591d989,0x591dba4,0x591de47,0x591dfa4};
static const char expected[]="e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55";
static int read_mem(uintptr_t p,void *out,SIZE_T n) {
 SIZE_T got=0;return p && n<=UINTPTR_MAX-p && ReadProcessMemory(GetCurrentProcess(),(void *)p,out,n,&got) && got==n;
}
static void record(Token t,int kind,uintptr_t out,int category) {
 LONG n=InterlockedCompareExchange(&written,0,0);if(n==LIMIT) return;
 Event *e=ring+n;GetSystemTime(&e->time);e->id=t.id;e->parent=t.parent;e->mask=t.mask;
 e->slot=t.slot;e->kind=kind;e->code=0;e->tag=0;e->category=category;e->readable=kind==1;e->code_valid=0;
 e->origin=t.origin;e->backend_status=t.backend_status;e->backend_status_valid=t.backend_status_valid;e->native_result=0;e->native_result_valid=0;
 if(kind==2 && out && out<=UINTPTR_MAX-48) {
  if(t.slot==1 || t.slot==4 || t.slot==7 || t.slot==12 || t.slot==13) {
   e->readable=read_mem(out,&e->tag,4) && (e->tag==1 || e->tag==2);
   /* Provider success contains an owned blob, NOT a status at +8. Never
    * inspect/log that payload. Only its tag is meaningful to this probe. */
   if(e->readable && (t.slot==1 || e->tag==1))
    e->code_valid=e->readable=read_mem(out+8,&e->code,4);
  } else if(t.slot!=8 && t.slot!=17) e->code_valid=e->readable=read_mem(out,&e->code,4);
 }
 MemoryBarrier();InterlockedExchange(&written,n+1);
}
static Token enter_metadata(int slot,uint32_t mask,int category,int origin,uintptr_t service) {
 DWORD error=GetLastError();Token t={0,0,mask,0,slot,origin,0};
 if(GetCurrentThreadId()==game_thread && state==ARMED && written<LIMIT) {
  ULONGLONG now=GetTickCount64();
  LONG active=InterlockedCompareExchange(&postpair_extension,0,0);
  /* Initial menu/backend capture is bounded separately from waiting for a
   * match. While quiet, only a selected prepare/connect can start recording.
   * Do not reset ring slots: old native fibers may still own return tokens. */
  int capturing=now<deadline || (active==1 && now<
      (ULONGLONG)InterlockedCompareExchange64(&postpair_deadline,0,0));
  if(!capturing && !(active==0 && now<idle_deadline && (slot==10 || slot==11))) {
   SetLastError(error);return t;
  }
  if(slot==5 && service<=UINTPTR_MAX-0x46c)
   t.backend_status_valid=read_mem(service+0x468,&t.backend_status,4);
  t.id=++serial;t.parent=slot?current_root:0;record(t,1,0,category);InterlockedIncrement(&inflight);
 }
 SetLastError(error);return t;
}
static Token enter(int slot,uint32_t mask,int category) {return enter_metadata(slot,mask,category,0,0);}
static unsigned postpair_begin(Token t) {
 unsigned previous=0;
 if(t.id) {
  /* One activation, including after the initial menu capture has gone quiet.
   * The worker treats -1 as unpublished, preventing a late-activation race. */
  DWORD error=GetLastError();
  if(InterlockedCompareExchange(&postpair_extension,-1,0)==0) {
   ULONGLONG until=GetTickCount64()+TRACE_MS,maximum=idle_deadline+TRACE_MS;
   InterlockedExchange64(&postpair_deadline,(LONG64)(until<maximum?until:maximum));
   InterlockedExchange(&postpair_extension,1);
  }
  previous=current_root;current_root=t.id;++postpair_depth;
  SetLastError(error);
 }
 return previous;
}
static void postpair_end(Token t,unsigned previous) {
 if(t.id) {--postpair_depth;if(current_root==t.id) current_root=previous;}
}
static Token enter_postpair(int slot) {
 /* Same-thread correlation only, not an assertion of native fiber ownership.
  * Unrelated calls outside a selected prepare/connect pass straight through. */
 if(GetCurrentThreadId()==game_thread && postpair_depth) return enter(slot,0,-1);
 Token empty={0};return empty;
}
static void leave(Token t,uintptr_t out) {
 DWORD error=GetLastError();
 if(t.id) {if(state==ARMED) record(t,2,out,-1);InterlockedDecrement(&inflight);}
 SetLastError(error);
}
static void *hook_check(uintptr_t a,uintptr_t out,uintptr_t mask,uintptr_t d,uintptr_t e,uintptr_t f) {
 Token t=enter(0,(uint32_t)mask,-1);unsigned previous=t.id?current_root:0;
 if(t.id) current_root=t.id;
 void *result=original_check(a,out,mask,d,e,f);
 if(t.id && current_root==t.id) current_root=previous;
 leave(t,out);return result;
}
static void *hook_platform(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 Token t=enter(1,0,-1);void *result=original_platform(a,out,c,d);leave(t,out);return result;
}
static void *hook_login(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,uintptr_t e,uintptr_t f) {
 Token t=enter(2,0,-1);void *result=original_login(a,out,c,d,e,f);leave(t,out);return result;
}
static void *hook_maintenance(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,uintptr_t e,uintptr_t category,
                              uintptr_t g,uintptr_t h,uintptr_t i) {
 Token t=enter(3,0,(unsigned char)category);void *result=original_maintenance(a,out,c,d,e,category,g,h,i);
 leave(t,out);return result;
}
static void *hook_provider(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t flags) {
 Token t=enter(4,0,-1);void *result=original_provider(a,out,c,flags);leave(t,out);return result;
}
static void *hook_backend(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,uintptr_t e,uintptr_t f,
                          uintptr_t g,uintptr_t h) {
 Token t=enter_metadata(5,0,-1,0,a);void *result=original_backend(a,out,c,d,e,f,g,h);leave(t,out);return result;
}
static void *hook_response(uintptr_t a,uintptr_t out,uintptr_t response) {
 Token t=enter(6,0,-1);void *result=original_response(a,out,response);leave(t,out);return result;
}
static void *hook_http(uintptr_t a,uintptr_t out,uintptr_t url,uintptr_t method,uintptr_t body,
                       uintptr_t headers,uintptr_t options) {
 Token t=enter(7,0,-1);void *result=original_http(a,out,url,method,body,headers,options);leave(t,out);return result;
}
static void *hook_error_string(uintptr_t a,uintptr_t b,uintptr_t c,uintptr_t d) {
 int origin=failure_origin((uintptr_t)__builtin_return_address(0),8);
#ifdef SZERO_SERVICE_TRACE_TEST
 origin=test_origin;
#endif
 if(!origin) return original_error_string(a,b,c,d);
 Token t=enter_metadata(8,0,-1,origin,0);void *result=original_error_string(a,b,c,d);
 leave(t,0);return result;
}
static void *hook_error_copy(uintptr_t out,uintptr_t source) {
 int origin=failure_origin((uintptr_t)__builtin_return_address(0),9);
#ifdef SZERO_SERVICE_TRACE_TEST
 origin=test_origin;
#endif
 if(!origin) return original_error_copy(out,source);
 Token t=enter_metadata(9,0,-1,origin,0);void *result=original_error_copy(out,source);
 leave(t,out);return result;
}
/* Selected original14599c540 continuation calls, not packet observers.
 * Both return a plain40-byte error in argument2. No identities, pointers,
 * request bodies, payloads or borrowed strings are recorded. */
static void *hook_connect(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,
                           uintptr_t e,uintptr_t f,uintptr_t g) {
 Token t=enter(10,0,-1);unsigned previous=postpair_begin(t);
 void *result=original_connect(a,out,c,d,e,f,g);postpair_end(t,previous);leave(t,out);return result;
}
static void *hook_peer_prepare(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 Token t=enter(11,0,-1);unsigned previous=postpair_begin(t);
 void *result=original_peer_prepare(a,out,c,d);postpair_end(t,previous);leave(t,out);return result;
}
/* Original member resolution and future wait both return TAGGED48; successful
 * tag2 contains pointers/borrowed state, never inspect it as an error. The wait
 * output is arg1, unlike member resolution's arg2. Original1459acbf0 projects
 * the future's completed plain40 error into arg2; commit/start are plain40 too.
 * All extra scalar args are forwarded, even when a selected body ignores them. */
static void *hook_member(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 Token t=enter_postpair(12);void *result=original_member(a,out,c,d);leave(t,out);return result;
}
static void *hook_wait(uintptr_t out,uintptr_t future) {
 Token t=enter_postpair(13);void *result=original_wait(out,future);leave(t,out);return result;
}
static void *hook_wait_result(uintptr_t future,uintptr_t out) {
 Token t=enter_postpair(14);void *result=original_wait_result(future,out);leave(t,out);return result;
}
static void *hook_commit(uintptr_t context,uintptr_t out) {
 Token t=enter_postpair(15);void *result=original_commit(context,out);leave(t,out);return result;
}
static void *hook_peer_start(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 Token t=enter_postpair(16);void *result=original_peer_start(a,out,c,d);leave(t,out);return result;
}
/* Exact reflected SSGameInstance::SetBattleResult: two scalar pointers,
 * no added arguments and no native state changes. FKoratBattleResult+0 is
 * EBattleWinLose (original enum0..7), not a native error/result code. Capture
 * the borrowed byte BEFORE original copy; publish only after it returns. */
static const char *result_names[8]={"None","Win","Lose","Draw","Timeup","RingOut","Win1P","Win2P"};
static void leave_battle_result(Token t,int readable,unsigned value) {
 DWORD error=GetLastError();
 if(t.id) {
  if(state==ARMED) {
   LONG n=InterlockedCompareExchange(&written,0,0);
   if(n<LIMIT) {
    Event *e=ring+n;memset(e,0,sizeof(*e));GetSystemTime(&e->time);
    e->id=t.id;e->parent=t.parent;e->slot=t.slot;e->kind=3;e->category=-1;
    e->readable=readable;e->native_result_valid=readable && value<8;
    if(e->native_result_valid)e->native_result=(int)value;
    MemoryBarrier();InterlockedExchange(&written,n+1);
   }
  }
  InterlockedDecrement(&inflight);
 }
 SetLastError(error);
}
static void *hook_battle_result(uintptr_t instance,uintptr_t borrowed) {
 Token t=enter(17,0,-1);DWORD error=GetLastError();unsigned char value=0;
 int readable=t.id && read_mem(borrowed,&value,1);
 SetLastError(error);
 void *result=original_battle_result(instance,borrowed);
 leave_battle_result(t,readable,value);return result;
}
static int sha256(const wchar_t *path,char hex[65]) {
 HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);
 BCRYPT_ALG_HANDLE alg=NULL;BCRYPT_HASH_HANDLE hash=NULL;unsigned char buf[65536],digest[32];DWORD n;int ok=0;
 if(f==INVALID_HANDLE_VALUE) return 0;
 if(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,NULL,0)<0 || BCryptCreateHash(alg,&hash,NULL,0,NULL,0,0)<0) goto done;
 for(;;) {if(!ReadFile(f,buf,sizeof(buf),&n,NULL)) goto done;if(!n) break;if(BCryptHashData(hash,buf,n,0)<0) goto done;}
 if(BCryptFinishHash(hash,digest,32,0)<0) goto done;
 for(unsigned i=0;i<32;i++) sprintf(hex+2*i,"%02x",digest[i]);
 ok=1;
done:if(hash) BCryptDestroyHash(hash);if(alg) BCryptCloseAlgorithmProvider(alg,0);CloseHandle(f);return ok;
}
static int flush(FILE *file) {
 LONG n=InterlockedCompareExchange(&written,0,0);
 while(consumed<(unsigned)n) {
  Event *e=ring+consumed++;
  fprintf(file,"{\"event\":\"%s\",\"time_utc\":\"%04u-%02u-%02uT%02u:%02u:%02u.%03uZ\",\"call\":%u,\"candidate_parent\":%u,\"boundary\":\"%s\",\"mask\":%u,\"category\":%d,\"readable\":%s,\"tag\":%u,\"code_valid\":%s,\"code\":%u,\"code_hex\":\"%08x\",\"failure_origin\":\"%s\",\"backend_status_valid\":%s,\"backend_status\":%u,\"native_battle_result_valid\":%s,\"native_battle_result\":%d,\"native_battle_result_name\":\"%s\"}\n",
   e->kind==1?"enter":e->kind==3?"native_battle_result":"return",e->time.wYear,e->time.wMonth,e->time.wDay,e->time.wHour,e->time.wMinute,e->time.wSecond,e->time.wMilliseconds,
   e->id,e->parent,names[e->slot],e->mask,e->category,e->readable?"true":"false",e->tag,e->code_valid?"true":"false",e->code,e->code,
   origins[e->origin],e->backend_status_valid?"true":"false",e->backend_status,
   e->native_result_valid?"true":"false",e->native_result,e->native_result_valid?result_names[e->native_result]:"unknown");
 }
 return fflush(file)==0 && !ferror(file);
}
static DWORD WINAPI worker(void *unused) {
 (void)unused;HANDLE handle=CreateFileW(log_path,GENERIC_WRITE,FILE_SHARE_READ,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
 if(handle==INVALID_HANDLE_VALUE) {InterlockedExchange(&state,FAILED);return 0;}
 int fd=_open_osfhandle((intptr_t)handle,0);if(fd<0) {CloseHandle(handle);InterlockedExchange(&state,FAILED);return 0;}
 FILE *file=_fdopen(fd,"w");if(!file) {_close(fd);InterlockedExchange(&state,FAILED);return 0;}
 wchar_t path[32768];char hash[65];int valid=GetModuleFileNameW(NULL,path,32768) && sha256(path,hash);
#ifndef SZERO_SERVICE_TRACE_TEST
 valid=valid && !strcmp(hash,expected);
#else
 (void)expected;(void)offsets;(void)prefixes;
#endif
 uintptr_t base=(uintptr_t)GetModuleHandleW(NULL);image_base=base;IMAGE_DOS_HEADER dos;IMAGE_NT_HEADERS64 nt;
 valid=valid && read_mem(base,&dos,sizeof(dos)) && dos.e_magic==IMAGE_DOS_SIGNATURE && dos.e_lfanew>0 &&
  (unsigned)dos.e_lfanew<1024*1024 && read_mem(base+(unsigned)dos.e_lfanew,&nt,sizeof(nt)) &&
  nt.Signature==IMAGE_NT_SIGNATURE && nt.OptionalHeader.Magic==IMAGE_NT_OPTIONAL_HDR64_MAGIC;
 DWORD size=valid?nt.OptionalHeader.SizeOfImage:0;
 wchar_t backend_mode[4];
 active_hooks=GetEnvironmentVariableW(L"SZERO_LAN_NATIVE_SESSION3",backend_mode,4)==1 && backend_mode[0]==L'1'?17:HOOKS;
 for(unsigned i=0;valid && i<active_hooks;i++) {
#ifndef SZERO_SERVICE_TRACE_TEST
  entries[i]=base+offsets[i];unsigned char bytes[16];
  valid=size>=16 && entries[i]>=base && entries[i]-base<=size-16 && read_mem(entries[i],bytes,16) && !memcmp(bytes,prefixes[i],16);
#else
  entries[i]=(uintptr_t)GetProcAddress((HMODULE)base,test_exports[i]);valid=entries[i]!=0;(void)size;
#endif
 }
#ifndef SZERO_SERVICE_TRACE_TEST
 for(unsigned i=0;valid && i<11;i++) {
  unsigned char instruction[5];int32_t displacement=0;uintptr_t after=base+origin_returns[i];
  valid=origin_returns[i]>=5 && origin_returns[i]<=size &&
   read_mem(after-5,instruction,5) && instruction[0]==0xe8;
  if(valid) {
   memcpy(&displacement,instruction+1,4);
   valid=(int64_t)after+displacement==(int64_t)entries[i<4?8:9];
  }
 }
#else
 (void)origin_returns;
#endif
 if(!valid) {fprintf(file,"{\"event\":\"refused\",\"reason\":\"unsupported_image_or_modified_probe_bytes\"}\n");fclose(file);InterlockedExchange(&state,FAILED);return 0;}
 fprintf(file,"{\"event\":\"header\",\"schema\":5,\"probe_revision\":\"postresult2\",\"sha256\":\"%s\",\"thread\":%lu,\"event_limit\":512,\"duration_ms\":%u,\"post_pair_extension_ms\":%u,\"pair_wait_ms\":%u,\"max_duration_ms\":%u,\"disk_patches\":false,\"mechanism\":\"temporary in-memory function wrappers\",\"coverage\":\"current game thread only; bounded recording; candidate_parent is inferred same-thread correlation\"}\n",hash,(unsigned long)game_thread,TRACE_MS,TRACE_MS,WAIT_MS,WAIT_MS+TRACE_MS);
 if(fflush(file)) {fclose(file);InterlockedExchange(&state,FAILED);return 0;}
 MH_STATUS init=MH_Initialize();
 if(init!=MH_OK) {fprintf(file,"{\"event\":\"refused\",\"reason\":\"hook_initialization_failed\",\"status\":%d}\n",init);fclose(file);InterlockedExchange(&state,FAILED);return 0;}
 void *hooks[HOOKS]={(void *)&hook_check,(void *)&hook_platform,(void *)&hook_login,(void *)&hook_maintenance,
  (void *)&hook_provider,(void *)&hook_backend,(void *)&hook_response,(void *)&hook_http,
  (void *)&hook_error_string,(void *)&hook_error_copy,(void *)&hook_connect,(void *)&hook_peer_prepare,
  (void *)&hook_member,(void *)&hook_wait,(void *)&hook_wait_result,(void *)&hook_commit,(void *)&hook_peer_start,(void *)&hook_battle_result};
 void **originals[HOOKS]={(void **)&original_check,(void **)&original_platform,(void **)&original_login,(void **)&original_maintenance,
  (void **)&original_provider,(void **)&original_backend,(void **)&original_response,(void **)&original_http,
  (void **)&original_error_string,(void **)&original_error_copy,(void **)&original_connect,(void **)&original_peer_prepare,
  (void **)&original_member,(void **)&original_wait,(void **)&original_wait_result,(void **)&original_commit,(void **)&original_peer_start,(void **)&original_battle_result};
 MH_STATUS status=MH_OK;
 for(unsigned i=0;i<active_hooks;i++) {status=MH_CreateHook((void *)entries[i],hooks[i],originals[i]);if(status!=MH_OK) break;}
 if(status==MH_OK) status=MH_EnableHook(MH_ALL_HOOKS);
 if(status!=MH_OK) {
  MH_STATUS rollback=MH_DisableHook(MH_ALL_HOOKS); /* Never free partially enabled trampolines. */
  fprintf(file,"{\"event\":\"refused\",\"reason\":\"hook_installation_failed\",\"status\":%d,\"rollback_status\":%d}\n",status,rollback);
  fclose(file);InterlockedExchange(&state,FAILED);return 0;
 }
 for(unsigned i=0;i<active_hooks;i++) memcpy(installed_prefix[i],(void *)entries[i],16);
 ULONGLONG started=GetTickCount64();
 deadline=started+TRACE_MS;idle_deadline=started+WAIT_MS;
 InterlockedExchange(&state,ARMED);fprintf(file,"{\"event\":\"ready\"}\n");fflush(file);
 int io_ok=1,endpoint_seen=0,bridge_stopped=0,waiting_logged=0,activation_logged=0;ULONGLONG next_check=0;
 for(;;) {
  LONG active=InterlockedCompareExchange(&postpair_extension,0,0);
  ULONGLONG now=GetTickCount64(),until=idle_deadline;
  if(active==1) {
   until=(ULONGLONG)InterlockedCompareExchange64(&postpair_deadline,0,0);
   if(until<deadline) until=deadline;
  }
  if(now>=until || written>=LIMIT) break;
  if(!waiting_logged && active==0 && now>=deadline) {
   fprintf(file,"{\"event\":\"waiting_for_pair\",\"remaining_ms\":%llu}\n",(unsigned long long)(idle_deadline-now));
   waiting_logged=1;
  }
  if(!activation_logged && active==1) {
   fprintf(file,"{\"event\":\"pair_capture_started\",\"remaining_ms\":%llu}\n",(unsigned long long)(until-now));
   activation_logged=1;
  }
  if(!flush(file)) {io_ok=0;break;}
  if(GetTickCount64()>=next_check) {
   int exists=GetFileAttributesW(endpoint_path)!=INVALID_FILE_ATTRIBUTES;
   if(endpoint_seen && !exists) {bridge_stopped=1;break;}
   endpoint_seen|=exists;next_check=GetTickCount64()+250;
  }
  Sleep(25);
 }
 InterlockedExchange(&state,STOPPING);
 int owned=1;for(unsigned i=0;i<active_hooks;i++) {unsigned char bytes[16];if(!read_mem(entries[i],bytes,16) || memcmp(bytes,installed_prefix[i],16)) owned=0;}
 status=owned?MH_DisableHook(MH_ALL_HOOKS):MH_ERROR_ENABLED;
 /* Disable failure leaves pass-through wrappers, not unhandled traps. */
 InterlockedExchange(&state,status==MH_OK?STOPPED:FAILED);flush(file);
 fprintf(file,"{\"event\":\"stopped\",\"restored\":%s,\"hook_status\":%d,\"ownership_retained\":%s,\"io_ok\":%s,\"inflight\":%ld,\"post_pair_extension_used\":%s,\"reason\":\"%s\"}\n",
  status==MH_OK?"true":"false",status,owned?"true":"false",io_ok?"true":"false",inflight,postpair_extension==1?"true":"false",
  !io_ok?"log_write_failed":bridge_stopped?"bridge_stopped":written>=LIMIT?"event_limit":postpair_extension==1?"capture_timeout":"pair_wait_timeout");
 fclose(file);return 0;
}
static int finish(DWORD error) {SetLastError(error);return 0;}
__declspec(dllexport) int szero_service_trace(void *lua) {
 (void)lua;DWORD error=GetLastError();if(state!=OFF) return finish(error);
 wchar_t enabled[4],id[40];HMODULE own=NULL;
 if(GetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",enabled,4)!=1 || enabled[0]!=L'1') return finish(error);
 if(GetEnvironmentVariableW(L"SZERO_LAN_SERVICE_TRACE",enabled,4)!=1 || enabled[0]!=L'1') return finish(error);
 if(GetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",id,40)!=32) return finish(error);
 for(unsigned i=0;i<32;i++) if(!((id[i]>=L'0'&&id[i]<=L'9')||(id[i]>=L'a'&&id[i]<=L'f'))) return finish(error);
 if(InterlockedCompareExchange(&state,VERIFYING,OFF)!=OFF) return finish(error);
 if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
    (const wchar_t *)(uintptr_t)&szero_service_trace,&own) || !GetModuleFileNameW(own,log_path,32768)) {
  InterlockedExchange(&state,FAILED);return finish(error);
 }
 wchar_t *slash=wcsrchr(log_path,L'\\');if(!slash || slash-log_path>32000) {InterlockedExchange(&state,FAILED);return finish(error);}
 wcscpy(endpoint_path,log_path);
 swprintf(endpoint_path+(slash-log_path)+1,200,L"lan_runtime_%ls.native.endpoint",id);
 swprintf(slash+1,200,L"native_service_trace_%ls.jsonl",id);game_thread=GetCurrentThreadId();
 HANDLE thread=CreateThread(NULL,0,worker,NULL,0,NULL);
 if(thread) CloseHandle(thread);else InterlockedExchange(&state,FAILED);
 return finish(error);
}
