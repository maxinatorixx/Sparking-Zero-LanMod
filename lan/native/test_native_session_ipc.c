/* Compiles actual session_operation/process_session_job. Synthetic native
 * ownership callbacks only; no game executable/functions or hash bypass. */
#define SZERO_SESSION_V3
#define SZERO_NATIVE_SESSION_IPC_TEST
#include "native_session_host.h"
static int fixture_provider_host(uintptr_t,SzeroStreamWire *,SzeroNativeSessionHost *,SzeroNativeSessionCallbacks *);
#include "native_search.c"
#include <assert.h>
static unsigned char fixture_task[0x100];
static int fixture_cancel,cache_calls,release_calls,string_destroys;
static int fixture_bad_pair,fixture_abort_not_ready,fixture_ready_value=1;
static uintptr_t fixture_pair[2];
static unsigned char fixture_descriptor_id[32];
static int fixture_lan_mode;
static unsigned fixture_member_capacity=2;
static int fixture_view_mode,fixture_view_empty;
static unsigned char fixture_lan_session[32];
static SzeroText fixture_text(const SzeroNativeString *s) {
 return (s->words[0]&1)?(SzeroText){(void *)s->words[1],(size_t)s->words[2]}:
  (SzeroText){(const unsigned char *)s+1,((const unsigned char *)s)[0]>>2};
}
static void fixture_deep_string(SzeroNativeString *out,const SzeroNativeString *in) {
 SzeroText text=fixture_text(in);memset(out,0,sizeof(*out));out->words[0]=1;
 out->words[1]=(uintptr_t)calloc(text.size+1,1);assert(out->words[1]);
 memcpy((void *)out->words[1],text.data,text.size);out->words[2]=out->words[3]=text.size;
}
static void fixture_free_string(SzeroNativeString *s) {if(s->words[0]&1) free((void *)s->words[1]);}
static void fixture_deep_descriptor(SzeroNativeDescriptor *out,const SzeroNativeDescriptor *in) {
 memcpy(out,in,sizeof(*out));fixture_deep_string(&out->id,&in->id);
 assert(in->properties.count==0);out->properties.buckets=(uintptr_t)&out->properties.inline_bucket;
 if(in->settings.numeric_count) {
  size_t size=(size_t)in->settings.numeric_count*4;
  out->settings.numeric=(uintptr_t)malloc(size);assert(out->settings.numeric);
  memcpy((void *)out->settings.numeric,(void *)in->settings.numeric,size);
 }
 if(in->settings.stream) {
  SzeroBorrowedStream *stream=malloc(sizeof(*stream));assert(stream);
  memcpy(stream,(void *)in->settings.stream,sizeof(*stream));
  stream->data=(uintptr_t)stream->bytes;out->settings.stream=(uintptr_t)stream;
 }
 for(unsigned j=0;j<2;j++) fixture_deep_string(out->owner_identity+j,in->owner_identity+j);
 SzeroNativeMemberNode *sentinel=(void *)&out->members,*previous=sentinel;
 const SzeroNativeMemberNode *source=in->members.next;
 out->members.next=out->members.previous=sentinel;
 for(size_t i=0;i<in->members.count;i++) {
  SzeroNativeMemberNode *node=calloc(1,sizeof(*node));assert(node);node->value=source->value;
  fixture_deep_string(&node->value.id,&source->value.id);
  for(unsigned j=0;j<2;j++) fixture_deep_string(node->value.identity+j,source->value.identity+j);
  fixture_deep_string(&node->value.address,&source->value.address);
  node->previous=previous;node->next=sentinel;previous->next=node;
  out->members.previous=node;previous=node;source=source->next;
 }
}
static void fixture_free_descriptor(SzeroNativeDescriptor *descriptor) {
 fixture_free_string(&descriptor->id);
 for(unsigned j=0;j<2;j++) fixture_free_string(descriptor->owner_identity+j);
 SzeroNativeMemberNode *node=descriptor->members.next;
 for(size_t i=0;i<descriptor->members.count;i++) {
  SzeroNativeMemberNode *next=node->next;fixture_free_string(&node->value.id);
  for(unsigned j=0;j<2;j++) fixture_free_string(node->value.identity+j);
  fixture_free_string(&node->value.address);free(node);node=next;
 }
 free((void *)descriptor->settings.numeric);free((void *)descriptor->settings.stream);
}
static void fixture_check_lan_view(const SzeroNativeDescriptor *descriptor,int own_count) {
 unsigned local=0,remote=0;const SzeroNativeMemberNode *node=descriptor->members.next;
 for(size_t i=0;i<descriptor->members.count;i++,node=node->next) {
  SzeroText first=fixture_text(node->value.identity),second=fixture_text(node->value.identity+1);
  if(first.size==17 && !memcmp(first.data,"76561198000000000",17)) {
   local++;assert(second.size==17 && !memcmp(second.data,"fixture-secondary",17));
  } else {assert(szero_lan_identity_valid(first.data,first.size));remote++;}
  if(node->value.owner) for(unsigned j=0;j<2;j++) {
   SzeroText owner=fixture_text(descriptor->owner_identity+j);
   SzeroText member=fixture_text(node->value.identity+j);
   assert(owner.size==member.size && !memcmp(owner.data,member.data,owner.size));
  }
 }
 assert(local==(unsigned)own_count && local+remote==descriptor->members.count);
 assert(descriptor->member_count==descriptor->members.count && descriptor->settings.capacity==fixture_member_capacity);
}
static void *fixture_current(void) {return fixture_task;}
static unsigned char fixture_yield(void *task) {
 assert(task==fixture_task);Sleep(1);
 LONG state=InterlockedCompareExchange(&job.state,0,0);
 if(fixture_abort_not_ready && (state==4 || state==5)) fixture_ready_value=0;
 return (fixture_cancel==1 && state==3) || (fixture_cancel==2 && (state==4 || state==5));
}
static void *fixture_copy(void *out,const void *in) {memcpy(out,in,40);return out;}
static int fixture_ready(void *unused) {(void)unused;return fixture_ready_value;}
static int fixture_validate(void *unused,const uintptr_t pair[2]) {
 (void)unused;return !fixture_bad_pair && pair[0]==fixture_pair[0] && pair[1]==fixture_pair[1] && pair[0]!=0;
}
static SzeroNativeResult *SZERO_NATIVE_CALL fixture_factory(SzeroNativeResult *out,
 uintptr_t unused,SzeroNativeResult *input) {
 (void)unused;assert(input->tag==2 && !fixture_pair[0]);
 const SzeroNativeDescriptor *descriptor=(const void *)input->payload[0];
 const SzeroNativeString *id=&descriptor->id;
 size_t id_size=(id->words[0]&1)?(size_t)id->words[2]:((const unsigned char *)id)[0]>>2;
 assert(id_size==32);
 memcpy(fixture_descriptor_id,(id->words[0]&1)?(void *)id->words[1]:(const unsigned char *)id+1,32);
 const SzeroBorrowedStream *stream=(const void *)descriptor->settings.stream;
 assert(stream && stream->vtable==base+SZERO_STREAM_VTABLE_RVA && stream->kind==1);
 assert(stream->size==(fixture_view_empty?0:32));
 assert(stream->read_cursor==(fixture_view_empty?0:3));
 assert(stream->write_cursor==(fixture_view_mode?0:29));
 for(unsigned i=0;i<stream->size;i++) assert(((unsigned char *)stream->data)[i]==(unsigned char)(i*7));
 fixture_pair[0]=(uintptr_t)calloc(1,0x100);fixture_pair[1]=fixture_pair[0]+0xe8;
 if(fixture_lan_mode) fixture_deep_descriptor((void *)fixture_pair[0],descriptor);
 assert(fixture_pair[0]);out->tag=2;out->payload[0]=fixture_pair[0];out->payload[1]=fixture_pair[1];return out;
}
static void fixture_localize(void *unused,uintptr_t desc) {
 (void)unused;assert(desc==fixture_pair[0]);
 if(fixture_lan_mode) fixture_check_lan_view((void *)desc,1);
}
static void fixture_string(void *unused,SzeroNativeString *out,SzeroText txt) {
 (void)unused;assert(txt.size==32);out->words[0]=1;
 out->words[1]=(uintptr_t)malloc(txt.size);assert(out->words[1]);
 memcpy((void *)out->words[1],txt.data,txt.size);out->words[2]=out->words[3]=txt.size;
}
static void fixture_release(void *unused,uintptr_t pair[2]) {
 (void)unused;assert(fixture_validate(NULL,pair));
 if(fixture_lan_mode) fixture_free_descriptor((void *)pair[0]);
 free((void *)pair[0]);
 fixture_pair[0]=fixture_pair[1]=0;pair[0]=pair[1]=0;release_calls++;
}
static void fixture_destroy_string(void *unused,SzeroNativeString *owned) {
 (void)unused;assert(owned->words[0]==1);free((void *)owned->words[1]);memset(owned,0,sizeof(*owned));string_destroys++;
}
static void fixture_cache(void *unused,uintptr_t pair[2]) {
 (void)unused;assert(InterlockedCompareExchange(&job.state,0,0)==5);
 if(fixture_lan_mode) {
  SzeroNativeDescriptor *descriptor=(void *)pair[0];fixture_check_lan_view(descriptor,1);
  SzeroText id=fixture_text(&descriptor->id);assert(id.size==32);
  memcpy(fixture_lan_session,id.data,32);
 }
 cache_calls++;fixture_release(NULL,pair);
}
static void fixture_clone(void *unused,SzeroNativeDescriptor *out,uintptr_t source) {
 (void)unused;assert(source==fixture_pair[0]);memset(out,0,sizeof(*out));
 if(fixture_lan_mode) {fixture_deep_descriptor(out,(void *)source);return;}
 fixture_string(NULL,&out->id,(SzeroText){fixture_descriptor_id,32});
}
static void fixture_diff(void *unused,SzeroNativeDescriptor *out,uint8_t settings) {
 (void)unused;(void)out;(void)settings;assert(0);
}
static int fixture_provider_host(uintptr_t service,SzeroStreamWire *stream,
 SzeroNativeSessionHost *host,SzeroNativeSessionCallbacks *cb) {
 (void)service;memset(host,0,sizeof(*host));memset(cb,0,sizeof(*cb));
 cb->ready=fixture_ready;cb->factory=fixture_factory;cb->stream=stream;cb->image_base=base;
 cb->validate_pair=fixture_validate;cb->localize=fixture_localize;
 cb->copy_string=fixture_string;cb->destroy_string=fixture_destroy_string;
 cb->cache_consume=fixture_cache;cb->release_pair=fixture_release;
 cb->clone_descriptor=fixture_clone;cb->diff_consume=fixture_diff;return 1;
}
static DWORD WINAPI fixture_worker(void *unused) {
 (void)unused;while(InterlockedCompareExchange(&job.state,0,0)!=1) Sleep(1);
 process_session_job();return 0;
}
int main(int argc,char **argv) {
 if(argc!=4 && argc!=5) {fputs("usage: fixture endpoint-path instance create|create-embedded|cancel|cancel-stage|search|match|join|bad-pair|abort-not-ready [sessionid]\n",stderr);return 2;}
 assert(strlen(argv[2])==32);strcpy(instance,argv[2]);
 assert(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,argv[1],-1,endpoint,32768));
 fixture_cancel=!strcmp(argv[3],"cancel")?1:!strcmp(argv[3],"cancel-stage")?2:0;
 fixture_bad_pair=!strcmp(argv[3],"bad-pair");fixture_abort_not_ready=!strcmp(argv[3],"abort-not-ready");
 if(fixture_abort_not_ready) fixture_cancel=2;
 int multi_creating=!strcmp(argv[3],"tournament-multi");
 int multi_rejoining=!strcmp(argv[3],"tournament-rejoin-multi");
 int multi_joining=!strcmp(argv[3],"tournament-join-multi") || multi_rejoining;
 if(multi_rejoining)sequence=100;
 int quick_multi=!strcmp(argv[3],"quickmatch-multi");
 native_lan_multi=multi_creating || multi_joining || quick_multi;
 fixture_member_capacity=(multi_creating || multi_joining)?8:2;
 fixture_lan_mode=!strcmp(argv[3],"quickmatch-lan") || native_lan_multi;native_lan_profile=fixture_lan_mode;
 int quickmatching=!strcmp(argv[3],"quickmatch") || !strcmp(argv[3],"quickmatch-lan") || quick_multi;
 int searching=!strcmp(argv[3],"search") || quickmatching;
 int embedding=!strcmp(argv[3],"create-embedded") || quickmatching;
 int inline64=!strcmp(argv[3],"create-inline64");
 int view_mode=!strcmp(argv[3],"create-view") || !strcmp(argv[3],"create-view-empty");
 fixture_view_mode=view_mode;fixture_view_empty=!strcmp(argv[3],"create-view-empty");
 int joining=!strcmp(argv[3],"join") || multi_joining,matching=!strcmp(argv[3],"match");
 assert(fixture_cancel || fixture_bad_pair || searching || joining || matching || embedding || inline64 || view_mode || multi_creating || !strcmp(argv[3],"create"));
 assert(!joining || (argc==5 && strlen(argv[4])==32));
 session_v3=1;game_thread=GetCurrentThreadId();base=0x140000000ULL;
 current_task=fixture_current;yield_cancel=fixture_yield;copy_error=fixture_copy;
 *(uint32_t *)(fixture_task+0x58)=0x1234;
 WSADATA w;assert(!WSAStartup(MAKEWORD(2,2),&w));
 SOCKET initial=connect_bridge();assert(initial!=INVALID_SOCKET);closesocket(initial);
 HANDLE worker_handle=CreateThread(NULL,0,fixture_worker,NULL,0,NULL);assert(worker_handle);
 SzeroNativeSettings settings={0};settings.capacity=(uint8_t)fixture_member_capacity;settings.compatibility=123;
 struct {
  uintptr_t vtable,reserved;uint64_t rd,wr;uintptr_t data;uint64_t size,capacity;uintptr_t allocator;
 } vector={0};
 unsigned char bytes[32];for(unsigned i=0;i<32;i++) bytes[i]=(unsigned char)(i*7);
 vector.vtable=base+SZERO_VECTOR_STREAM_VTABLE_RVA;vector.rd=3;vector.wr=29;
 vector.data=(uintptr_t)bytes;vector.size=32;vector.capacity=64;
 settings.stream=(uintptr_t)&vector;
 struct {
  uintptr_t vtable,reserved;uint64_t rd,wr,size,capacity;unsigned char bytes[32];
 } embedded={0};
 embedded.vtable=base+SZERO_EMBEDDED_STREAM_VTABLE_RVA;embedded.rd=3;embedded.wr=29;
 embedded.size=embedded.capacity=32;memcpy(embedded.bytes,bytes,32);
 if(embedding) settings.stream=(uintptr_t)&embedded;
 struct {
  uintptr_t vtable,reserved;uint64_t rd,wr;uint32_t kind,padding;
  uintptr_t data;uint64_t size,capacity;unsigned char bytes[32];
 } compact={0};
 _Static_assert(sizeof(compact)-sizeof(compact.bytes)==0x40,"inline64 byte offset");
 compact.vtable=base+SZERO_INLINE64_STREAM_VTABLE_RVA;compact.rd=3;compact.wr=29;
 compact.kind=1;compact.data=(uintptr_t)compact.bytes;compact.size=compact.capacity=32;
 memcpy(compact.bytes,bytes,32);
 if(inline64) settings.stream=(uintptr_t)&compact;
 struct {uintptr_t vt,reserved;uint64_t rd,size;uintptr_t data;} view={0};
 view.vt=base+SZERO_VIEW_STREAM_VTABLE_RVA;
 if(!strcmp(argv[3],"create-view")) {view.rd=3;view.size=32;view.data=(uintptr_t)bytes;}
 if(view_mode) settings.stream=(uintptr_t)&view;
 unsigned char query[0x50]={0};*(uint32_t *)query=123;
 if(fixture_lan_mode) {query[0x4d]=1;query[0x4e]=255;}
 unsigned char stats[40];memset(stats,0x6b,sizeof(stats));
 unsigned char storage[80];memset(storage,0xa5,sizeof(storage));
 SzeroNativeResult *output=(void *)(storage+8);memset(output,0,joining?40:48);
 uintptr_t id_view[2]={(uintptr_t)(joining?argv[4]:NULL),joining?32:0};
 session_operation((void *)1,output,joining?(void *)id_view:searching?(void *)query:&settings,
  matching?(void *)query:searching?(void *)(stats+8):NULL,0,joining?2:searching?3:matching?4:1);
 assert(WaitForSingleObject(worker_handle,10000)==WAIT_OBJECT_0);CloseHandle(worker_handle);
 if(quickmatching) {
  assert(output->tag==2 && output->payload[1]<=1 && !cache_calls);
  joining=output->payload[1]!=0;unsigned char selected_id[32];
  assert(provider_search_request==1 && provider_search_return_count==joining && provider_search_return_result==0);
  if(joining) {
   /* This deliberately minimal mock clones ONLY the ID. Inspecting the
    * actual vector must detect its missing fields instead of trusting DTO. */
   assert(provider_inspection_read==1 && provider_copy_mask==(fixture_lan_mode?0:114));
   assert(provider_numeric_pass==1 && provider_self_exclusion==0);
   SzeroNativeDescriptor *selected=(void *)output->payload[0];
   if(fixture_lan_mode) fixture_check_lan_view(selected,0);
   assert(selected && selected->id.words[0]==1 && selected->id.words[2]==32);
   memcpy(selected_id,(void *)selected->id.words[1],32);
   if(fixture_lan_mode) {fixture_free_descriptor(selected);string_destroys++;}
   else fixture_destroy_string(NULL,&selected->id);
   free(selected);
  }
  memset(storage,0xa5,sizeof(storage));memset(output,0,joining?40:48);
  worker_handle=CreateThread(NULL,0,fixture_worker,NULL,0,NULL);assert(worker_handle);
  uintptr_t selected_view[2]={(uintptr_t)selected_id,32};
  if(joining) block_join((void *)1,output,selected_view,fixture_lan_mode?0x28:0);
  else session_operation((void *)1,output,&settings,NULL,0,1);
  assert(WaitForSingleObject(worker_handle,10000)==WAIT_OBJECT_0);CloseHandle(worker_handle);
  /* Later create/join MUST NOT erase the finite-search evidence. */
  assert(provider_search_request==1 && provider_search_return_count==joining && provider_search_return_result==0);
  if(joining) {
   assert(provider_join_attempts==1 && provider_join_flags==(fixture_lan_mode?0x28:0) && provider_join_code==0);
   printf("V3 native join flags=%ld code=%ld\n",(long)provider_join_flags,(long)provider_join_code);
   assert(provider_inspection_read==1 && provider_copy_mask==(fixture_lan_mode?0:114));
  }
  printf("V3 quickmatch action=%s search_count=%d\n",joining?"join":"create",joining);
  if(fixture_lan_mode) printf("V3 LAN session=%.*s own=1 peer=%d copy=%ld self=%ld\n",
   32,fixture_lan_session,joining,(long)provider_copy_mask,(long)provider_self_exclusion);
  searching=0;
 }
 if(embedding && !joining) assert(provider_stream_info.layout==SZERO_STREAM_EMBEDDED && !provider_stream_info.refusal);
 if(inline64) assert(provider_stream_info.layout==SZERO_STREAM_INLINE64 && !provider_stream_info.refusal);
 if(view_mode) assert(provider_stream_info.layout==SZERO_STREAM_VIEW && !provider_stream_info.refusal);
 if(fixture_cancel) {assert(output->tag==1 && output->payload[0]==0x1234 && !cache_calls);}
 else if(fixture_bad_pair) {assert(output->tag==1 && output->payload[0]==0x413 && !cache_calls);}
 else if(joining) {assert(((SzeroNativeError *)output)->code==0 && cache_calls==1 && string_destroys==(quickmatching?1:0));}
 else if(searching) {
  assert(output->tag==2 && !cache_calls && stats[8]==(output->payload[1]?1:0));
  assert(provider_search_request==1 && provider_search_return_result==SZERO_ADAPTER_OK);
  assert(provider_search_return_count==(output->payload[1]?1:0));
  uint64_t count=1;memcpy(&count,stats+16,8);assert(count==0);
  memcpy(&count,stats+24,8);assert(count==0);
  for(size_t i=0;i<8;i++) assert(stats[i]==0x6b);
  for(size_t i=9;i<16;i++) assert(stats[i]==0x6b);
  for(size_t i=32;i<sizeof(stats);i++) assert(stats[i]==0x6b);
  if(output->payload[0]) {
   fixture_destroy_string(NULL,&((SzeroNativeDescriptor *)output->payload[0])->id);
   free((void *)output->payload[0]);
  }
 }
 else {assert(output->tag==2 && cache_calls==1);SzeroNativeString id;memcpy(&id,output->payload,sizeof(id));fixture_destroy_string(NULL,&id);}
 for(size_t i=0;i<8;i++) assert(storage[i]==0xa5);
 for(size_t i=8+(joining?40:48);i<sizeof(storage);i++) assert(storage[i]==0xa5);
 if(fixture_bad_pair || fixture_abort_not_ready) {
  assert(provider_stopped && fixture_pair[0] && !cache_calls);
  assert(provider_quarantined_stage.handle.payload[0]==fixture_pair[0]);
  if(fixture_abort_not_ready) {
   assert(provider_quarantined_stage.state==SZERO_STAGE_PREPARED);
   assert(provider_quarantined_callbacks.context==&provider_quarantined_host);
   assert(!provider_quarantined_callbacks.stream);
   fixture_destroy_string(NULL,&provider_quarantined_stage.id);
  }
  /* Fixture-owned memory only: production never guesses a quarantine free. */
  free((void *)fixture_pair[0]);fixture_pair[0]=fixture_pair[1]=0;
  memset(output,0,48);session_operation((void *)1,output,&settings,NULL,0,1);
  assert(output->tag==1 && output->payload[0]==0x413 && !cache_calls && job.state==0);
 }
 assert(!fixture_pair[0]);
 printf("V3 fixture mode=%s cache=%d releases=%d destroyed=%d state=%ld\n",argv[3],cache_calls,release_calls,string_destroys,job.state);
 WSACleanup();return 0;
}
