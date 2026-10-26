/* Actual lifecycle include, owned service memory and synthetic native callbacks.
 * No game image, platform method, actual native allocator or socket is invoked. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <stdlib.h>
#include "native_session_host.h"
#include "native_session_codec.h"
#define SZERO_NATIVE_SESSION_LIFECYCLE_TEST
#define NATIVE_IPC_MAX 16384
static uintptr_t base=0x140000000ULL;
static DWORD game_thread;
static int thread_mismatches,queue_drains;
static int provider_native_thread(void) {
 if(GetCurrentThreadId()==game_thread) return 1;
 thread_mismatches++;return 0;
}
static volatile LONG verification=2;
static volatile LONG sequence;
static int native_lan_multi;
static int provider_decode(const char *frame,SzeroSessionCodec *codec) {
 return szero_session_decode((const unsigned char *)frame,strlen(frame),codec);
}
static struct {volatile LONG state,cancel,hook_done; LONG id; char begin[NATIVE_IPC_MAX];} job;
static struct {char frame[SZERO_SESSION_FRAME_MAX];int kind,empty;unsigned game_port,proxy_port;volatile LONG background;} session_job;
typedef struct {uintptr_t object,original,table[28];} Replacement;
static Replacement replacements[1];static unsigned replacement_count=1;
static int provider_owns(void *unused,uintptr_t object,uintptr_t vptr) {
 (void)unused;
 return object==replacements[0].object && vptr==(uintptr_t)replacements[0].table;
}
static unsigned char service[0x300],task[0x100];
static uintptr_t bundle[2],platform[1],platform_table[13];
static uintptr_t selected_service;
static SzeroNativeDescriptor active;
static SzeroNativeMemberNode local_node;
static int readiness_calls,readiness_failure,cache_removals,diffs,clones,releases,matches,creates;
static int capture_refused;
static uint64_t consumed_stream_cursor;
static volatile LONG stop_worker,force_empty;
static char last_request[NATIVE_IPC_MAX];
static const char sid[]="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
static const char frame[]="SESSION3 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 123 0 2 0 0 0 0 0 - 1 "
 "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 0 616263 646566 3132372e302e302e313a31323334 7 1 9 0 1\n";
static int read_mem(uintptr_t source,void *out,size_t size) {
 SIZE_T got=0;return source && ReadProcessMemory(GetCurrentProcess(),(void *)source,out,size,&got) && got==size;
}
static int provider_read(uintptr_t source,void *out,size_t size,void *unused) {(void)unused;return read_mem(source,out,size);}
static int append(char *out,size_t *used,const char *format,...) {
 va_list args;va_start(args,format);int count=vsnprintf(out+*used,NATIVE_IPC_MAX-*used,format,args);va_end(args);
 if(count<0 || (size_t)count>=NATIVE_IPC_MAX-*used) return 0;
 *used+=(size_t)count;return 1;
}
static int provider_hex(char *out,size_t *used,const unsigned char *bytes,size_t size) {
 if(!size) return append(out,used,"-");
 for(size_t i=0;i<size;i++) if(!append(out,used,"%02x",bytes[i])) return 0;
 return 1;
}
static void *unavailable(void *out,int tagged) {
 memset(out,0,tagged?48:40);*(uint32_t *)((char *)out+(tagged?8:0))=0x413;
 if(tagged) *(uint32_t *)out=1;
 return out;
}
static void *current_task(void) {return task;}
static unsigned char yield_cancel(void *given) {assert(given==task);Sleep(1);return 0;}
static void *copy_error(void *out,const void *input) {memcpy(out,input,40);return out;}
static int provider_identity(uintptr_t self,SzeroIdentityWire *out) {
 assert(self==(uintptr_t)service);memset(out,0,sizeof(*out));
 memcpy(out->value[0].bytes,"abc",3);memcpy(out->value[1].bytes,"def",3);
 out->value[0].size=out->value[1].size=3;return 1;
}
static int ready(void *unused) {(void)unused;return 1;}
static SzeroNativeResult *SZERO_NATIVE_CALL factory(SzeroNativeResult *out,uintptr_t unused,SzeroNativeResult *input) {
 (void)unused;assert(input->tag==2);out->tag=2;out->payload[0]=(uintptr_t)calloc(1,0x100);
 assert(out->payload[0]);out->payload[1]=out->payload[0]+0xe8;return out;
}
static int validate_pair(void *unused,const uintptr_t pair[2]) {(void)unused;return pair[0] && pair[1]==pair[0]+0xe8;}
static void localize(void *unused,uintptr_t ptr) {(void)unused;assert(ptr);}
static void clone(void *unused,SzeroNativeDescriptor *out,uintptr_t ptr) {(void)unused;assert(ptr);memset(out,0,sizeof(*out));clones++;}
static void release(void *unused,uintptr_t pair[2]) {(void)unused;free((void *)pair[0]);pair[0]=pair[1]=0;releases++;}
static void diff(void *unused,SzeroNativeDescriptor *owned,uint8_t settings) {
 (void)unused;(void)owned;assert(settings==1);diffs++;consumed_stream_cursor=0;
}
static void copy_string(void *unused,SzeroNativeString *out,SzeroText input) {(void)unused;(void)out;(void)input;assert(0);}
static void cache(void *unused,uintptr_t pair[2]) {(void)unused;(void)pair;assert(0);}
static int provider_host(uintptr_t self,SzeroStreamWire *stream,SzeroNativeSessionHost *host,SzeroNativeSessionCallbacks *cb) {
 if(self!=(uintptr_t)service || self!=selected_service) return 0;
 memset(host,0,sizeof(*host));memset(cb,0,sizeof(*cb));cb->ready=ready;cb->factory=factory;cb->stream=stream;cb->image_base=base;
 cb->validate_pair=validate_pair;cb->localize=localize;cb->clone_descriptor=clone;
 cb->release_pair=release;cb->diff_consume=diff;cb->copy_string=copy_string;cb->cache_consume=cache;return 1;
}
static int provider_addresses(SzeroSessionCodec *codec,uintptr_t self) {(void)codec;return self==(uintptr_t)service;}
static int fixture_lifecycle_remove_cache(uintptr_t self,const unsigned char id[32]) {
 assert(self==(uintptr_t)service && !memcmp(id,sid,32));
 memset(service+0x218,0,16);memset(service+0x200,0,8);cache_removals++;return 1;
}
static void fixture_lifecycle_base_tick(void *self) {
 assert(self==service);queue_drains++;
}
static void *SZERO_NATIVE_CALL fixture_readiness(void *self,void *out) {
 assert(self==platform);memset(out,0,40);*(uint32_t *)out=readiness_failure?0x413:0;readiness_calls++;return out;
}
static void *SZERO_NATIVE_CALL fixture_wrong_c8(void *self,void *out,const void *a,const void *b) {
 (void)self;(void)out;(void)a;(void)b;assert(0 && "service+c8 is not readiness");return NULL;
}
static void *SZERO_NATIVE_CALL fixture_teardown(void *self,void *out) {
 assert(self==service);return fixture_readiness(platform,out);
}
static SIZE_T fixture_query(const void *input,PMEMORY_BASIC_INFORMATION out,SIZE_T size) {
 assert(input && size==sizeof(*out));memset(out,0,size);
 out->State=MEM_COMMIT;out->Type=MEM_IMAGE;out->AllocationBase=(void *)base;out->Protect=PAGE_EXECUTE_READ;return size;
}
#define VirtualQuery fixture_query
static void *session_operation(void *self,void *out,const void *settings,const void *query,uint16_t flags,int kind) {
 assert(self==service && settings && flags==3);
 if(capture_refused) return unavailable(out,1);
 if(kind==4) {assert(query);matches++;}else {assert(kind==1 && !query);creates++;}
 memset(out,0,48);*(uint32_t *)out=2;return out;
}
#include "native_session_frames.inc"
#include "native_session_lifecycle.inc"
#undef VirtualQuery
static DWORD WINAPI scripted_worker(void *unused) {
 (void)unused;
 while(!InterlockedCompareExchange(&stop_worker,0,0)) {
  if(InterlockedCompareExchange(&job.state,0,0)!=1) {Sleep(1);continue;}
  strcpy(last_request,job.begin);strcpy(session_job.frame,frame);
  session_job.empty=InterlockedCompareExchange(&force_empty,0,0);
  InterlockedExchange(&job.state,3);
  while(!InterlockedCompareExchange(&job.hook_done,0,0)) Sleep(1);
  Sleep(20);InterlockedExchange(&job.state,0);
 }
 return 0;
}
static void idle(void) {while(InterlockedCompareExchange(&job.state,0,0)) Sleep(1);}
static void inject_background(const char *snapshot,int empty) {
 idle();strcpy(session_job.frame,snapshot);session_job.empty=empty;
 lifecycle_background_service=(uintptr_t)service;session_job.background=1;job.hook_done=0;
 InterlockedExchange(&job.state,3);lifecycle_finish_background();assert(job.hook_done);
 InterlockedExchange(&job.state,0);InterlockedExchange(&session_job.background,0);
}
static void set_active(void) {
 active.id.words[0]=1;active.id.words[1]=(uintptr_t)sid;active.id.words[2]=32;
 uintptr_t ptr=(uintptr_t)&active;memcpy(service+0x218,&ptr,8);
 uint64_t count=1;memcpy(service+0x200,&count,8);
 SzeroNativeMemberNode *sentinel=(void *)&active.members;
 local_node.next=local_node.previous=sentinel;
 active.members.next=active.members.previous=&local_node;active.members.count=1;
 local_node.value.identity[0].words[0]=3<<2;memcpy((char *)&local_node.value.identity[0]+1,"abc",3);
 local_node.value.identity[1].words[0]=3<<2;memcpy((char *)&local_node.value.identity[1]+1,"def",3);
 local_node.value.address.words[0]=14<<2;memcpy((char *)&local_node.value.address+1,"127.0.0.1:1234",14);
 local_node.value.field_88=7;local_node.value.optional_present=1;local_node.value.optional_value=9;local_node.value.owner=1;
 active.member_count=1;active.settings.capacity=2;
}
int main(void) {
 game_thread=GetCurrentThreadId();uintptr_t table[28]={0};
 table[25]=(uintptr_t)fixture_wrong_c8;table[12]=(uintptr_t)fixture_teardown;
 platform_table[12]=(uintptr_t)fixture_readiness;platform[0]=(uintptr_t)platform_table;
 bundle[1]=(uintptr_t)platform;uintptr_t bundle_ptr=(uintptr_t)bundle;
 memcpy(service+8,&bundle_ptr,8);
 replacements[0].object=(uintptr_t)service;replacements[0].original=(uintptr_t)table;
 selected_service=(uintptr_t)service;
 uintptr_t owned_vptr=(uintptr_t)replacements[0].table;memcpy(service,&owned_vptr,8);
 set_active();HANDLE worker=CreateThread(NULL,0,scripted_worker,NULL,0,NULL);assert(worker);
 uintptr_t view[2]={(uintptr_t)sid,32};SzeroNativeError out={0};
 /* Reproduce the Windows distinction: original+c8 has the wrong ABI and
  * must NEVER be consulted for readiness. Missing platform fails closed. */
 uintptr_t saved_platform=bundle[1];bundle[1]=0;
 lifecycle_readiness(service,&out);assert(out.code==0x413 && readiness_calls==0);
 bundle[1]=saved_platform;
 lifecycle_platform_operation(service,&out,NULL,NULL);assert(out.code==0x413 && readiness_calls==0);
 lifecycle_flags(service,&out,view,2);assert(!out.code && strstr(last_request,"FLAGS3 ") && diffs==1);
 consumed_stream_cursor=9;
 /* No idle: the scripted worker intentionally recycles 20ms AFTER hook_done.
  * The next real native callback must drain, not spuriously return0x413. */
 lifecycle_fence(service,&out,(void *)1);assert(!out.code && diffs==1 && readiness_calls==1 && consumed_stream_cursor==9);idle();
 lifecycle_flags(service,&out,view,2);assert(!out.code && diffs==1 && consumed_stream_cursor==9);idle();
 lifecycle_tick(service);assert(queue_drains==1);
 while(InterlockedCompareExchange(&job.state,0,0)!=3) Sleep(1);
 lifecycle_tick(service);assert(queue_drains==2);
 int before=diffs;lifecycle_tick(service);assert(diffs==before && queue_drains==3);
 assert(lifecycle_wait_background(task,&out,0) && !session_job.background && diffs==1 && consumed_stream_cursor==9);
 lifecycle_tick(service);assert(queue_drains==4 && !job.state); /* Cooldown. */
 uintptr_t active_ptr=0;memcpy(service+0x218,&active_ptr,8);
 lifecycle_tick(service);assert(queue_drains==5 && !job.state); /* No session. */
 DWORD saved_thread=game_thread;game_thread=0;
 lifecycle_tick(service);assert(queue_drains==6 && thread_mismatches==1 && !job.state);
 game_thread=saved_thread;set_active();
 uintptr_t unowned_vptr=0;memcpy(service,&unowned_vptr,8);
 lifecycle_tick(service);assert(queue_drains==6 && !job.state); /* Fail closed. */
 memcpy(service,&owned_vptr,8);
 before=diffs;int allocations_before=clones;
 inject_background(frame,0);assert(diffs==before && clones==allocations_before && consumed_stream_cursor==9);
 char changed[sizeof(frame)];strcpy(changed,frame);char *flags=strstr(changed," 7 1 9 ");assert(flags);flags[1]='8';
 inject_background(changed,0);assert(diffs==before+1 && !consumed_stream_cursor);
 consumed_stream_cursor=17;
 inject_background(changed,0);assert(diffs==before+1 && consumed_stream_cursor==17); /* No second reset. */
 flags[1]='9';selected_service=0;
 inject_background(changed,0);assert(diffs==before+1 && consumed_stream_cursor==17); /* Stale origin. */
 selected_service=(uintptr_t)service;
 inject_background(changed,0);assert(diffs==before+2);
 char foreign[sizeof(frame)];strcpy(foreign,changed);foreign[9]='d';
 consumed_stream_cursor=23;
 inject_background(foreign,0);assert(diffs==before+2 && consumed_stream_cursor==23);
 assert(!provider_frame_same((uintptr_t)service,foreign));
 int before_settings=diffs;
 struct {uint64_t present;SzeroNativeSettings settings;} optional={0};optional.present=1;optional.settings.capacity=2;
 optional.settings.numeric=(uintptr_t)malloc(4);optional.settings.numeric_count=optional.settings.numeric_capacity=1;
 *(int32_t *)optional.settings.numeric=42;
 lifecycle_settings(service,&out,view,&optional);
 assert(!out.code && strstr(last_request,"UPDATESETTINGS3 ") && strstr(last_request," 7 1 9\n") && diffs==before_settings+1);idle();
 assert(optional.settings.numeric && optional.settings.numeric_capacity==1 && *(int32_t *)optional.settings.numeric==42);
 consumed_stream_cursor=55;int before_explicit=diffs;
 lifecycle_control(service,&out,8,0,&optional.settings);idle();
 assert(!out.code && diffs==before_explicit+1 && !consumed_stream_cursor); /* Explicit reset intent. */
 free((void *)optional.settings.numeric); /* Original caller's one cleanup. */
 SzeroNativeSettings settings={0};settings.capacity=2;SzeroNativeResult match={0};
 lifecycle_match(service,&match,&settings,(void *)1,3);assert(match.tag==2 && matches==1);
 readiness_failure=1;lifecycle_match(service,&match,&settings,(void *)1,3);
 assert(match.tag==1 && match.payload[0]==0x413 && matches==1);readiness_failure=0;
 /* Production +88 borrows: outer1458c84a0, not our hook, owns destruction.
  * Invalid/unsupported settings must never call a guessed native destructor. */
 unsigned char settings_before[sizeof(settings)];
 settings.numeric=(uintptr_t)1;settings.numeric_capacity=1; /* Unreadable capture. */
 memcpy(settings_before,&settings,sizeof(settings));capture_refused=1;
 lifecycle_create(service,&match,&settings,3);
 assert(match.tag==1 && creates==0 && !memcmp(settings_before,&settings,sizeof(settings)));
 capture_refused=0;settings.numeric=0;settings.numeric_capacity=0;
 memcpy(settings_before,&settings,sizeof(settings));
 lifecycle_create(service,&match,&settings,3);assert(match.tag==2 && creates==1);
 assert(!memcmp(settings_before,&settings,sizeof(settings)));
 readiness_failure=1;lifecycle_create(service,&match,&settings,3);
 assert(match.tag==1 && match.payload[0]==0x413 && creates==1);readiness_failure=0;
 SzeroNativeResult left={0};lifecycle_leave(service,&left,view);
 assert(left.tag==2 && !left.payload[0] && cache_removals==1 && strstr(last_request,"LEAVE3 "));
 lifecycle_fence(service,&out,(void *)1);assert(!out.code && !job.state); /* No-session handoff also drains. */
 assert(!provider_frame_same((uintptr_t)service,frame));
 int ready_before=readiness_calls;job.hook_done=0;InterlockedExchange(&job.state,-1);
 lifecycle_fence(service,&out,(void *)1);assert(out.code==0x413 && readiness_calls==ready_before);
 InterlockedExchange(&job.state,0); /* Ongoing foreground must not fake a completed fence. */
 set_active();lifecycle_teardown(service,&out);assert(!out.code && cache_removals==2);idle();
 set_active();provider_frame_mark((uintptr_t)service,frame);inject_background(frame,1);
 assert(cache_removals==3 && !provider_frame_same((uintptr_t)service,frame));
 assert(clones==releases && clones==diffs);
 InterlockedExchange(&stop_worker,1);assert(WaitForSingleObject(worker,5000)==WAIT_OBJECT_0);CloseHandle(worker);
 puts("native lifecycle actual include contracts passed");return 0;
}
