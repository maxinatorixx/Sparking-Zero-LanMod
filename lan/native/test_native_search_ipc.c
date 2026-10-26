/* Production Win64 IPC primitives against a real Python bridge; no game code. */
#include "native_search.c"
#include <assert.h>

static DWORD WINAPI fixture_job(void *unused) {(void)unused;process_job();return 0;}

int main(int argc,char **argv) {
 if(argc==3 && !strcmp(argv[1],"logcheck")) {
  assert(MultiByteToWideChar(CP_UTF8,0,argv[2],-1,report_path,32768));
  assert(GetFileAttributesW(report_path)==INVALID_FILE_ATTRIBUTES);
  SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",L"0");report("quiet");
  assert(GetFileAttributesW(report_path)==INVALID_FILE_ATTRIBUTES);
  SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",L"1");report("enabled");
  assert(GetFileAttributesW(report_path)!=INVALID_FILE_ATTRIBUTES);assert(DeleteFileW(report_path));
  puts("Native report logging gate passed");return 0;
 }

 if(argc!=4) return 90;
 if(!MultiByteToWideChar(CP_UTF8,0,argv[1],-1,endpoint,32768)) return 91;
 if(strlen(argv[2])!=32) return 92;
 strcpy(instance,argv[2]);
 WSADATA w;if(WSAStartup(MAKEWORD(2,2),&w)) return 93;
 int worker_mode=!strncmp(argv[3],"worker_",7);
 const char *mode=worker_mode?argv[3]+7:argv[3];
 unsigned char query[0x50]={0},filter[16]={0},pairs[32]={0};
 uint32_t compatibility=42;uint64_t pointer=(uintptr_t)filter,count=1,key=123;
 int32_t comparison=0,value=-5;
 memcpy(query,&compatibility,4);memcpy(query+8,&pointer,8);
 memcpy(query+0x10,&count,8);memcpy(query+0x18,&count,8);
 memcpy(filter,&key,8);memcpy(filter+8,&comparison,4);memcpy(filter+12,&value,4);
 if(!strcmp(mode,"compound")) {
  uint64_t pair_pointer=(uintptr_t)pairs;
  memcpy(pairs,filter,16);memcpy(pairs+16,filter,16);
  memcpy(query+0x28,&pair_pointer,8);memcpy(query+0x30,&count,8);memcpy(query+0x38,&count,8);
 }
 char line[NATIVE_IPC_MAX],reply[128];
 if(!query_line((uintptr_t)query,1,line)) return 96;
 printf("request=%s",line);fflush(stdout);
 if(worker_mode) {
  job.id=1;strcpy(job.begin,line);InterlockedExchange(&job.state,1);
  HANDLE h=CreateThread(NULL,0,fixture_job,NULL,0,NULL);if(!h) return 101;
  ULONGLONG deadline=GetTickCount64()+7000;
  while(ipc_phase!=IPC_PENDING && job.state!=2 && GetTickCount64()<deadline) Sleep(10);
  if(!strcmp(mode,"reject")) {
   if(job.state!=2 || ipc_error!=IPC_ENDPOINT_INVALID) return 102;
   Sleep(100);if(job.state!=2 || WaitForSingleObject(h,0)!=WAIT_TIMEOUT) return 103;
  } else if(ipc_phase!=IPC_PENDING || job.state!=1) {
   fprintf(stderr,"worker phase=%ld error=%ld code=%ld state=%ld\n",ipc_phase,ipc_error,ipc_error_code,job.state);
   return 104;
  }
  InterlockedExchange(&job.cancel,1);InterlockedExchange(&job.hook_done,1);
  if(WaitForSingleObject(h,5000)!=WAIT_OBJECT_0 || job.state!=0) return 105;
  if(strcmp(mode,"reject") && (ipc_phase!=IPC_CLOSED || ipc_error!=IPC_OK)) return 106;
  CloseHandle(h);puts("worker ownership and cleanup passed");WSACleanup();return 0;
 }
 SOCKET s=connect_bridge();
 if(!strcmp(mode,"reject")) {
  if(s!=INVALID_SOCKET) {closesocket(s);return 94;}
  puts("rejected endpoint");return 0;
 }
 if(s==INVALID_SOCKET) {fprintf(stderr,"connect_bridge failed: %d phase=%ld error=%ld code=%ld\n",WSAGetLastError(),ipc_phase,ipc_error,ipc_error_code);return 95;}
 if(!send_line(s,line) || !receive_line(s,reply,sizeof(reply))) return 97;
 printf("reply=%s",reply);fflush(stdout);
 const char *expected="PENDING 1\n";
 if(strcmp(reply,expected)) return 98;
 if(!strcmp(expected,"PENDING 1\n") && strcmp(mode,"disconnect")) {
  if(!send_line(s,"CANCEL 1\n") || !receive_line(s,reply,sizeof(reply))) return 99;
  printf("cancel=%s",reply);if(strcmp(reply,"CANCELLED 1\n")) return 100;
 }
 closesocket(s);WSACleanup();return 0;
}
