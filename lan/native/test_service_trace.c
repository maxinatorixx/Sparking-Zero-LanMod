#define SZERO_SERVICE_TRACE_TEST
#include "service_trace.c"
typedef struct {uint32_t words[12];} Result;
static volatile LONG calls,exceptions;
static void *main_fiber;static int pause_fiber,fiber_done,deep_route,deep_connect,late_connect;
#define EXPORTED __declspec(dllexport) __attribute__((noinline))
EXPORTED void *trace_battle_result(uintptr_t instance,uintptr_t borrowed) {
 if(instance!=0x1234 || GetLastError()!=1234) ExitProcess(201);
 (void)borrowed;InterlockedIncrement(&calls);SetLastError(2468);return (void *)0xabcdef01;
}
static DWORD WINAPI result_other_thread(void *unused) {
 (void)unused;unsigned char value=1;SetLastError(1234);
 return trace_battle_result(0x1234,(uintptr_t)&value)==(void *)0xabcdef01 && GetLastError()==2468?0:1;
}
EXPORTED void *trace_member(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 if(a!=1 || c!=3 || d!=4) ExitProcess(80);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=2;r->words[2]=0xdeadbeef;
 InterlockedIncrement(&calls);return (void *)333;
}
EXPORTED void *trace_wait(uintptr_t out,uintptr_t future) {
 if(future!=2) ExitProcess(81);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=2;r->words[2]=0xdeadbeef;
 InterlockedIncrement(&calls);return (void *)444;
}
EXPORTED void *trace_wait_result(uintptr_t future,uintptr_t out) {
 if(future!=1) ExitProcess(82);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=0x90;
 InterlockedIncrement(&calls);return (void *)555;
}
EXPORTED void *trace_commit(uintptr_t context,uintptr_t out) {
 if(context!=1) ExitProcess(83);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=0x800fa;
 InterlockedIncrement(&calls);return (void *)666;
}
EXPORTED void *trace_peer_start(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 if(a!=1 || c!=3 || d!=4) ExitProcess(84);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=0x57c3a7bb;
 InterlockedIncrement(&calls);return (void *)777;
}
EXPORTED void *trace_connect(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,
                              uintptr_t e,uintptr_t f,uintptr_t g) {
 if(a!=1 || c!=3 || d!=4 || e!=5 || f!=6 || g!=7) ExitProcess(70);
 if(deep_connect) {
  Result nested;
  if(trace_member(1,(uintptr_t)&nested,3,4)!=(void *)333 || nested.words[0]!=2 || nested.words[2]!=0xdeadbeef) ExitProcess(85);
  if(trace_wait((uintptr_t)&nested,2)!=(void *)444 || nested.words[0]!=2 || nested.words[2]!=0xdeadbeef) ExitProcess(86);
  if(trace_wait_result(1,(uintptr_t)&nested)!=(void *)555 || nested.words[0]!=0x90) ExitProcess(87);
  if(trace_peer_start(1,(uintptr_t)&nested,3,4)!=(void *)777 || nested.words[0]!=0x57c3a7bb) ExitProcess(88);
  if(trace_commit(1,(uintptr_t)&nested)!=(void *)666 || nested.words[0]!=0x800fa) ExitProcess(89);
 }
 if(late_connect) Sleep(600);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=0x800fa;
 InterlockedIncrement(&calls);return (void *)111;
}
EXPORTED void *trace_peer_prepare(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 if(a!=1 || c!=3 || d!=4) ExitProcess(71);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=0x37980004;
 InterlockedIncrement(&calls);return (void *)222;
}
EXPORTED void *trace_error_string(uintptr_t a,uintptr_t b,uintptr_t c,uintptr_t d) {
 if(a!=1 || b!=2 || c!=3 || d!=4) ExitProcess(60);
 InterlockedIncrement(&calls);return (void *)741;
}
EXPORTED void *trace_error_copy(uintptr_t out,uintptr_t source) {
 memcpy((void *)out,(void *)source,sizeof(Result));InterlockedIncrement(&calls);return (void *)852;
}
EXPORTED void *trace_http(uintptr_t a,uintptr_t out,uintptr_t url,uintptr_t method,uintptr_t body,
                          uintptr_t headers,uintptr_t options) {
 if(a!=1 || url!=3 || method!=4 || body!=5 || headers!=6 || options!=7) ExitProcess(61);
 test_origin=1;
 if(trace_error_string(1,2,3,4)!=(void *)741) ExitProcess(62);
 test_origin=7;Result error={0},copied;
 error.words[0]=0x57c80000;
 if(trace_error_copy((uintptr_t)&copied,(uintptr_t)&error)!=(void *)852 || copied.words[0]!=0x57c80000) ExitProcess(63);
 test_origin=0;Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=1;r->words[2]=copied.words[0];
 InterlockedIncrement(&calls);return (void *)963;
}
EXPORTED void *trace_provider(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t flags) {
 if(a!=1 || c!=3 || (flags!=4 && flags!=5)) ExitProcess(46);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));
 r->words[0]=flags==4?1:2;r->words[2]=flags==4?0x57c80000:0xdeadbeef;
 InterlockedIncrement(&calls);return (void *)135;
}
EXPORTED void *trace_response(uintptr_t a,uintptr_t out,uintptr_t response) {
 if(a!=1 || response!=3) ExitProcess(47);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=0x57c80000;
 InterlockedIncrement(&calls);return (void *)654;
}
EXPORTED void *trace_backend(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,uintptr_t e,uintptr_t f,
                            uintptr_t g,uintptr_t h) {
 if(a!=1 || c!=3 || d!=4 || e!=5 || f!=6 || g!=7 || h!=8) ExitProcess(48);
 if(trace_response(1,out,3)!=(void *)654) ExitProcess(49);
 InterlockedIncrement(&calls);return (void *)321;
}
EXPORTED void *trace_login(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,uintptr_t e,uintptr_t f) {
 if(a!=1 || c!=3 || d!=4 || e!=5 || f!=6) ExitProcess(20);
 if(deep_route) {
  Result provider;
  if(trace_provider(1,(uintptr_t)&provider,3,deep_route==1?4:5)!=(void *)135) ExitProcess(53);
  if(provider.words[0]==1) {
   memset((void *)out,0,sizeof(Result));((Result *)out)->words[0]=provider.words[2];
  } else if(trace_backend(1,out,3,4,5,6,7,8)!=(void *)321) ExitProcess(54);
  InterlockedIncrement(&calls);return (void *)123;
 }
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=0x57c80000;
 InterlockedIncrement(&calls);return (void *)123;
}
EXPORTED void *trace_platform(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d) {
 if(a!=1 || c!=3 || d!=4) ExitProcess(21);
 Result *r=(Result *)out;memset(r,0,sizeof(*r));r->words[0]=2;r->words[2]=0x90;
 InterlockedIncrement(&calls);return (void *)456;
}
EXPORTED void *trace_maintenance(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,uintptr_t e,
                                  uintptr_t category,uintptr_t g,uintptr_t h,uintptr_t i) {
 if(a!=1 || c!=3 || d!=4 || e!=5 || category!=2 || g!=7 || h!=8 || i!=9) ExitProcess(22);
 if(trace_login(1,out,3,4,5,6)!=(void *)123) ExitProcess(23);
 InterlockedIncrement(&calls);return (void *)789;
}
EXPORTED void *trace_check(uintptr_t a,uintptr_t out,uintptr_t mask,uintptr_t d,uintptr_t e,uintptr_t f) {
 if(a!=1 || d!=4 || e!=5 || f!=6 || (mask!=32 && mask!=4 && mask!=8)) ExitProcess(24);
 Result platform;if(trace_platform(1,(uintptr_t)&platform,3,4)!=(void *)456) ExitProcess(25);
 if(platform.words[0]!=2 || platform.words[2]!=0x90) ExitProcess(26);
 if(pause_fiber && GetCurrentThreadId()==game_thread) SwitchToFiber(main_fiber);
 if(trace_maintenance(1,out,3,4,5,2,7,8,9)!=(void *)789) ExitProcess(27);
 if(((Result *)out)->words[0]!=0x57c80000) ExitProcess(28);
 InterlockedIncrement(&calls);return (void *)987;
}
static LONG WINAPI handler(EXCEPTION_POINTERS *p) {
 if(p->ExceptionRecord->ExceptionCode==0xe1234567) {InterlockedIncrement(&exceptions);return EXCEPTION_CONTINUE_EXECUTION;}
 return EXCEPTION_CONTINUE_SEARCH;
}
static DWORD WINAPI other_thread(void *unused) {
 (void)unused;Result out;return trace_check(1,(uintptr_t)&out,32,4,5,6)==(void *)987?0:1;
}
static void WINAPI fiber(void *unused) {
 (void)unused;Result out;
 if(trace_check(1,(uintptr_t)&out,32,4,5,6)!=(void *)987) ExitProcess(30);
 fiber_done=1;SwitchToFiber(main_fiber);
}
int wmain(int argc,wchar_t **argv) {
 if(argc!=3 && argc!=4) return 2;
 SetEnvironmentVariableW(L"SZERO_LAN_NATIVE_SESSION3",!wcscmp(argv[2],L"operational")?L"1":NULL);
 SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",L"1");SetEnvironmentVariableW(L"SZERO_LAN_SERVICE_TRACE",NULL);SetLastError(4321);
 szero_service_trace(NULL);if(GetLastError()!=4321 || state!=OFF) return 3;
 SetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",argv[1]);SetEnvironmentVariableW(L"SZERO_LAN_SERVICE_TRACE",L"1");
 /* The logging opt-in is independently required even with trace/instance set. */
 SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",NULL);SetLastError(4321);
 szero_service_trace(NULL);if(GetLastError()!=4321 || state!=OFF) return 202;
 SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",L"0");
 szero_service_trace(NULL);if(GetLastError()!=4321 || state!=OFF) return 203;
 SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",L"1");
 wchar_t endpoint_file[32768];GetModuleFileNameW(NULL,endpoint_file,32768);
 wchar_t *slash=wcsrchr(endpoint_file,L'\\');if(!slash) return 44;
 swprintf(slash+1,200,L"lan_runtime_%ls.native.endpoint",argv[1]);
 HANDLE endpoint=CreateFileW(endpoint_file,GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
 if(endpoint==INVALID_HANDLE_VALUE) return 45;
 CloseHandle(endpoint);
 unsigned char original[HOOKS][32];
 for(unsigned i=0;i<HOOKS;i++) memcpy(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32);
 if(argc==4) {
  if(!wcscmp(argv[2],L"quietproduction")) SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",L"0");
  HMODULE dll=LoadLibraryW(argv[3]);if(!dll) return 40;
  typedef int (*Entry)(void *);Entry fn=(Entry)(uintptr_t)GetProcAddress(dll,"szero_service_trace");
  if(!fn) return 41;
  SetLastError(4321);fn(NULL);if(GetLastError()!=4321) return 42;
  Sleep(300);
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 43;
  return 0;
 }
 AddVectoredExceptionHandler(1,handler);
 for(unsigned i=0;i<200 && state!=ARMED && state!=FAILED;i++) {szero_service_trace(NULL);Sleep(10);}
 if(state!=ARMED) return 4;
 if(!wcscmp(argv[2],L"operational")) {
  if(active_hooks!=17 || memcmp(original[17],(void *)&trace_battle_result,32))return 213;
  unsigned char value=1;SetLastError(1234);
  if(trace_battle_result(0x1234,(uintptr_t)&value)!=(void *)0xabcdef01 || GetLastError()!=2468 || written)return 214;
  Sleep(350);DeleteFileW(endpoint_file);for(unsigned i=0;i<400 && (state==ARMED || state==STOPPING);i++)Sleep(10);
  if(state!=STOPPED)return 215;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32))return 216;
  puts("Operational backend retains exclusive result setter ownership");return 0;
 }
 if(!wcscmp(argv[2],L"battle_result")) {
  struct {unsigned char before,value,after;} borrowed={0xa5,0,0x5a};
  for(unsigned value=0;value<8;value++) {
   borrowed.value=(unsigned char)value;SetLastError(1234);
   if(trace_battle_result(0x1234,(uintptr_t)&borrowed.value)!=(void *)0xabcdef01 || GetLastError()!=2468 ||
      borrowed.before!=0xa5 || borrowed.value!=value || borrowed.after!=0x5a) return 204;
  }
  borrowed.value=255;SetLastError(1234);
  if(trace_battle_result(0x1234,(uintptr_t)&borrowed.value)!=(void *)0xabcdef01 || GetLastError()!=2468 || borrowed.value!=255) return 205;
  void *unreadable=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_NOACCESS);
  if(!unreadable)return 206;
  SetLastError(1234);
  if(trace_battle_result(0x1234,(uintptr_t)unreadable)!=(void *)0xabcdef01 || GetLastError()!=2468)return 207;
  VirtualFree(unreadable,0,MEM_RELEASE);SetLastError(1234);
  if(trace_battle_result(0x1234,0)!=(void *)0xabcdef01 || GetLastError()!=2468)return 208;
  LONG before=written;HANDLE other=CreateThread(NULL,0,result_other_thread,NULL,0,NULL);DWORD exit_code=1;
  if(!other || WaitForSingleObject(other,3000)!=WAIT_OBJECT_0 || !GetExitCodeThread(other,&exit_code) || exit_code || written!=before)return 209;
  CloseHandle(other);Sleep(2600);
  if(state!=STOPPED || written!=22 || calls!=12 || inflight)return 210;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32))return 211;
  SetLastError(1234);
  if(trace_battle_result(0x1234,(uintptr_t)&borrowed.value)!=(void *)0xabcdef01 || GetLastError()!=2468 || written!=22 || calls!=13)return 212;
  puts("borrowed battle result enum forwarding and read-only scope passed");return 0;
 }
 if(!wcscmp(argv[2],L"postpairdeep") || !wcscmp(argv[2],L"postpairlate")) {
  late_connect=!wcscmp(argv[2],L"postpairlate");deep_connect=1;
  struct {uint64_t before;Result result;uint64_t after;} output={0};
  output.before=0x123456789abcdefULL;output.after=0xfedcba987654321ULL;
  /* Exact inner functions outside a selected prepare/connect must delegate. */
  if(trace_member(1,(uintptr_t)&output.result,3,4)!=(void *)333 ||
     trace_wait((uintptr_t)&output.result,2)!=(void *)444 ||
     trace_wait_result(1,(uintptr_t)&output.result)!=(void *)555 ||
     trace_peer_start(1,(uintptr_t)&output.result,3,4)!=(void *)777 ||
     trace_commit(1,(uintptr_t)&output.result)!=(void *)666 || written) return 90;
  if(late_connect) {
   /* Reproduce ef680: first connection begins AFTER initial capture expires. */
   Sleep(1500);
   if(state!=ARMED || written) return 97;
   SetLastError(1234);
   if(trace_check(1,(uintptr_t)&output.result,32,4,5,6)!=(void *)987 ||
      GetLastError()!=1234 || written) return 98;
  }
  SetLastError(1234);
  if(trace_connect(1,(uintptr_t)&output.result,3,4,5,6,7)!=(void *)111 ||
     output.result.words[0]!=0x800fa || GetLastError()!=1234) return 91;
  if(output.before!=0x123456789abcdefULL || output.after!=0xfedcba987654321ULL || postpair_depth) return 92;
  if(written!=12 || calls!=11+(late_connect?4:0) || postpair_extension!=1 ||
     (ULONGLONG)postpair_deadline>idle_deadline+TRACE_MS) return 93;
  LONG64 extension=postpair_deadline;
  /* A second outer entry cannot restart the extension indefinitely. */
  if(trace_peer_prepare(1,(uintptr_t)&output.result,3,4)!=(void *)222 ||
     postpair_deadline!=extension) return 94;
  Sleep(1400);
  if(state!=STOPPED || written!=14 || calls!=12+(late_connect?4:0) || inflight) return 95;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 96;
  puts("inner connection boundaries and single bounded late extension passed");return 0;
 }
 if(!wcscmp(argv[2],L"postpair")) {
  struct {uint64_t before;Result result;uint64_t after;} output={0};
  output.before=0x123456789abcdefULL;output.after=0xfedcba987654321ULL;
  SetLastError(1234);
  if(trace_connect(1,(uintptr_t)&output.result,3,4,5,6,7)!=(void *)111 ||
     output.result.words[0]!=0x800fa || GetLastError()!=1234) return 72;
  if(trace_peer_prepare(1,(uintptr_t)&output.result,3,4)!=(void *)222 ||
     output.result.words[0]!=0x37980004 || GetLastError()!=1234) return 73;
  if(output.before!=0x123456789abcdefULL || output.after!=0xfedcba987654321ULL) return 74;
  Sleep(1400);
  if(state!=STOPPED || calls!=2 || written!=4) return 75;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 76;
  puts("post-pair scalar forwarding and untouched error results passed");return 0;
 }
 if(!wcscmp(argv[2],L"transport")) {
  static const uintptr_t markers[]={0x591ccde,0x591d089,0x591d25e,0x591e0be,
   0x591d4d5,0x591d677,0x591d83c,0x591d989,0x591dba4,0x591de47,0x591dfa4};
  for(unsigned i=0;i<11;i++) {
   int slot=i<4?8:9;uintptr_t at=image_base+markers[i];
   if(failure_origin(at,slot)!=(int)i+1 || failure_origin(at-1,slot) ||
      failure_origin(at+1,slot) || failure_origin(at,slot==8?9:8)) return 64;
  }
  Result out;SetLastError(1234);
  if(trace_http(1,(uintptr_t)&out,3,4,5,6,7)!=(void *)963 || GetLastError()!=1234 ||
     out.words[0]!=1 || out.words[2]!=0x57c80000) return 65;
  LONG before=written;
  if(trace_error_string(1,2,3,4)!=(void *)741 || written!=before || GetLastError()!=1234) return 66;
  unsigned char *service=VirtualAlloc(NULL,8192,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
  if(!service) return 69;
  *(uint32_t *)(service+0x468)=0x80088;
  Token token=enter_metadata(5,0,-1,0,(uintptr_t)service);leave(token,(uintptr_t)&out);
  *(uint32_t *)(service+0x468)=0x57c80000;
  token=enter_metadata(5,0,-1,0,(uintptr_t)service);leave(token,(uintptr_t)&out);
  token=enter_metadata(5,0,-1,0,UINTPTR_MAX);leave(token,(uintptr_t)&out);
  VirtualFree(service,0,MEM_RELEASE);
  Sleep(2600);if(state!=STOPPED || calls!=4 || written!=12) return 67;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 68;
  puts("transport origin classification and forwarding passed");return 0;
 }
 if(!wcscmp(argv[2],L"deep")) {
  Result out;SetLastError(1234);
  deep_route=1;
  if(trace_login(1,(uintptr_t)&out,3,4,5,6)!=(void *)123 || out.words[0]!=0x57c80000 || GetLastError()!=1234) return 55;
  if(calls!=2) return 56; /* provider failure must not submit backend login */
  deep_route=2;
  if(trace_login(1,(uintptr_t)&out,3,4,5,6)!=(void *)123 || out.words[0]!=0x57c80000 || GetLastError()!=1234) return 57;
  Sleep(2600);if(state!=STOPPED || calls!=6 || written!=12) return 58;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 59;
  puts("identical outer errors distinguished at provider and backend boundaries");return 0;
 }
 if(!wcscmp(argv[2],L"fiber")) {
  main_fiber=ConvertThreadToFiber(NULL);void *child=CreateFiber(16384,fiber,NULL);
  if(!main_fiber || !child) return 31;
  pause_fiber=1;SwitchToFiber(child);pause_fiber=0;
  if(inflight!=1 || written!=3) return 32;
  Sleep(2600);if(state!=STOPPED) return 33;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 34;
  SwitchToFiber(child);DeleteFiber(child);ConvertFiberToThread();
  printf("suspended fiber resumed unchanged after trace stop\n");return fiber_done && calls==4?0:35;
 }
 if(!wcscmp(argv[2],L"cap")) {
  for(unsigned i=0;i<100;i++) {Result out;trace_check(1,(uintptr_t)&out,32,4,5,6);}
  Sleep(200);if(state!=STOPPED || written!=LIMIT || calls!=400) return 36;
  for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 37;
  printf("event cap preserved all calls and restored instructions\n");return 0;
 }
 unsigned masks[3]={32,4,8};
 for(unsigned i=0;i<3;i++) {Result out;SetLastError(1234);
  if(trace_check(1,(uintptr_t)&out,masks[i],4,5,6)!=(void *)987 || GetLastError()!=1234) return 5;
 }
 Result deep;SetLastError(1234);
 if(trace_provider(1,(uintptr_t)&deep,3,4)!=(void *)135 || GetLastError()!=1234 ||
    deep.words[0]!=1 || deep.words[2]!=0x57c80000) return 50;
 if(trace_provider(1,(uintptr_t)&deep,3,5)!=(void *)135 || GetLastError()!=1234 ||
    deep.words[0]!=2 || deep.words[2]!=0xdeadbeef) return 51;
 if(trace_backend(1,(uintptr_t)&deep,3,4,5,6,7,8)!=(void *)321 || GetLastError()!=1234 ||
    deep.words[0]!=0x57c80000) return 52;
 HANDLE thread=CreateThread(NULL,0,other_thread,NULL,0,NULL);
 if(!thread || WaitForSingleObject(thread,3000)!=WAIT_OBJECT_0) return 6;
 CloseHandle(thread);RaiseException(0xe1234567,0,0,NULL);
 if(!wcscmp(argv[2],L"stop")) {
  Sleep(1500);if(state!=ARMED) return 99;DeleteFileW(endpoint_file);
  for(unsigned i=0;i<100 && state!=STOPPED;i++) Sleep(10);
 } else Sleep(2600);
 if(state!=STOPPED) return 7;
 for(unsigned i=0;i<HOOKS;i++) if(memcmp(original[i],(void *)GetProcAddress(GetModuleHandleW(NULL),test_exports[i]),32)) return 8;
 Result out;trace_check(1,(uintptr_t)&out,32,4,5,6);
 printf("service trace contracts passed calls=%ld exceptions=%ld events=%ld\n",calls,exceptions,written);
 return calls==24 && written==32 && exceptions==1?0:9;
}
