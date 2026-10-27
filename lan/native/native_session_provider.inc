/* Developer-only live dispatch, compiled with SZERO_SESSION_V3. All network
 * work is confined to worker; native ownership never leaves the hook thread.
 * Lifecycle/transport sources are linked, but the original game's native
 * callbacks and combat remain unverified. Explicit experimental opt-in only. */
#include "native_session_frames.inc"
static int provider_read(uintptr_t p,void *out,size_t n,void *unused) {
 (void)unused;return read_mem(p,out,n);
}
static int provider_owns(void *unused,uintptr_t service,uintptr_t vptr) {
 (void)unused;
 for(unsigned n=0;n<replacement_count;n++)
  if(replacements[n].object==service && (uintptr_t)replacements[n].table==vptr) return 1;
 return 0;
}
static int provider_hex(char *dst,size_t *used,const unsigned char *bytes,size_t size) {
 if(size>4096) return 0;
 if(!size) return append(dst,used,"-");
 for(size_t i=0;i<size;i++) if(!append(dst,used,"%02x",bytes[i])) return 0;
 return 1;
}
static int provider_identity(uintptr_t service,SzeroIdentityWire *identity) {
#ifdef SZERO_NATIVE_SESSION_IPC_TEST
 (void)service;memset(identity,0,sizeof(*identity));
 if(native_lan_profile) {
  memcpy(identity->value[0].bytes,"76561198000000000",17);identity->value[0].size=17;
 } else {memcpy(identity->value[0].bytes,instance,32);identity->value[0].size=32;}
 memcpy(identity->value[1].bytes,"fixture-secondary",17);identity->value[1].size=17;
 return 1;
#else
 uintptr_t bundle=0,user=0;
 return read_mem(service+8,&bundle,8) && read_mem(bundle+0x18,&user,8) &&
  szero_capture_identity_pair(user+0x200,provider_read,NULL,identity)==SZERO_WIRE_OK &&
  identity->value[0].size<=64 && identity->value[1].size<=64;
#endif
}
static int provider_member(char *line,size_t *used,const SzeroIdentityWire *identity) {
 char address[32];int n=snprintf(address,sizeof(address),"127.0.0.1:%u",session_job.game_port);
 if(n<=0 || (size_t)n>=sizeof(address) || !session_job.game_port) return 0;
 return append(line,used," ") &&
  provider_hex(line,used,identity->value[0].bytes,(size_t)identity->value[0].size) && append(line,used," ") &&
  provider_hex(line,used,identity->value[1].bytes,(size_t)identity->value[1].size) && append(line,used," ") &&
  provider_hex(line,used,(const unsigned char *)address,(size_t)n) && append(line,used," 0 0 0");
}
#include "native_lan_userinfo_provider.inc"
static int provider_query(char *line,size_t *used,uintptr_t query,LONG id) {
 char *raw=malloc(NATIVE_IPC_MAX);if(!raw) return 0;
 int ok=query_line(query,id,raw);char *payload=ok?strchr(raw,' '):NULL;
 payload=payload?strchr(payload+1,' '):NULL;
 if(!payload) ok=0;
 else { size_t len=strlen(++payload);if(len && payload[len-1]=='\n') payload[len-1]=0;
  ok=append(line,used,"%s",payload); }
 free(raw);return ok;
}
static int provider_default_normalize(uintptr_t service,unsigned *normalize) {
#ifdef SZERO_NATIVE_SESSION_IPC_TEST
 (void)service;*normalize=0;return 1;
#else
 /* The outer search wrapper re-filters results using original service+40.
  * Steam/standard LOCAL return false; fallback LOCAL returns true. Never
  * hardcode the former for every service or invoke an arbitrary callback. */
 uintptr_t owned=0,target=0;
 if(!normalize || !read_mem(service,&owned,8) || !provider_owns(NULL,service,owned)) return 0;
 for(unsigned n=0;n<replacement_count;n++) if(replacements[n].object==service) {
  if(!read_mem(replacements[n].original+0x40,&target,8)) return 0;
  if(target==base+szero_bind_rva(0x11072d0)) {*normalize=0;return 1;}
  if(target==base+szero_bind_rva(0x10fdcc0)) {*normalize=1;return 1;}
  return 0;
 }
 return 0;
#endif
}
static int provider_request(uintptr_t service,const void *input,const void *extra,
 uint16_t flags,int kind,LONG id) {
 size_t used=0;SzeroIdentityWire identity;unsigned normalize=0;
 memset(&provider_stream_info,0,sizeof(provider_stream_info));
 provider_capture_fail(CAPTURE_SERIALIZATION,0);
 if((kind==3 || kind==4) && !provider_default_normalize(service,&normalize))
  return provider_capture_fail(CAPTURE_QUERY,0);
 if(kind==3) {
  int ok=append(job.begin,&used,"SEARCH3 %ld %u ",id,normalize) &&
   provider_query(job.begin,&used,(uintptr_t)input,id) && append(job.begin,&used,"\n");
  provider_capture_fail(ok?CAPTURE_NONE:CAPTURE_QUERY,0);return ok;
 }
 if(!provider_identity(service,&identity)) return provider_capture_fail(CAPTURE_IDENTITY,0);
 if(kind==2) {
  uintptr_t view[2];unsigned char sid[32];
  if(!read_mem((uintptr_t)input,view,sizeof(view)) || view[1]!=32 || !read_mem(view[0],sid,32)) return 0;
  for(unsigned i=0;i<32;i++) if(!((sid[i]>='0'&&sid[i]<='9')||(sid[i]>='a'&&sid[i]<='f'))) return 0;
  int ok=append(job.begin,&used,"JOIN3 %ld %.*s",id,32,(const char *)sid) &&
   provider_member(job.begin,&used,&identity) && append(job.begin,&used,"\n");
  if(ok) provider_capture_fail(CAPTURE_NONE,0);
  return ok;
 }
 SzeroSettingsWire *settings=calloc(1,sizeof(*settings));if(!settings) return 0;
 int rc=szero_capture_settings_info((uintptr_t)input,base,provider_read,NULL,settings,&provider_stream_info);
 if(rc!=SZERO_WIRE_OK) {
  free(settings);return provider_capture_fail(rc==SZERO_WIRE_UNSUPPORTED_STREAM?CAPTURE_STREAM_UNSUPPORTED:
   rc==SZERO_WIRE_UNREADABLE?CAPTURE_SETTINGS_UNREADABLE:CAPTURE_SETTINGS_INVALID,rc);
 }
 if(settings->numeric_count>16 || !settings->capacity ||
    settings->capacity>(native_lan_multi?SZERO_MATERIALIZER_MAX_MEMBERS:2) ||
    (!native_lan_multi && settings->capacity!=2)) {
  LONG reason=settings->numeric_count>16?CAPTURE_NUMERIC_LIMIT:CAPTURE_CAPACITY;
  LONG value=settings->numeric_count>16?(LONG)settings->numeric_count:(LONG)settings->capacity;
  free(settings);return provider_capture_fail(reason,value);
 }
 int ok=
  append(job.begin,&used,"%s %ld %lu %llu",kind==4?"MATCH3":"CREATE3",id,
   (unsigned long)settings->compatibility,(unsigned long long)settings->numeric_count);
 for(size_t i=0;ok && i<settings->numeric_count;i++) ok=append(job.begin,&used," %ld",(long)settings->numeric[i]);
 if(ok) ok=append(job.begin,&used," %u 0 %u %llu %llu %llu ",settings->capacity,settings->stream.present,
  (unsigned long long)settings->stream.size,(unsigned long long)settings->stream.read_cursor,
  (unsigned long long)settings->stream.write_cursor) &&
  provider_hex(job.begin,&used,settings->stream.bytes,(size_t)settings->stream.size) &&
  provider_member(job.begin,&used,&identity) && append(job.begin,&used," %u",flags);
 if(ok && kind==4) ok=append(job.begin,&used," %u ",normalize) && provider_query(job.begin,&used,(uintptr_t)extra,id);
 if(ok) ok=append(job.begin,&used,"\n");
 free(settings);if(ok) provider_capture_fail(CAPTURE_NONE,0);return ok;
}
/* One bounded native ownership quarantine. Once populated no further native
 * allocation is admitted, so failed cleanup cannot accumulate hidden leaks.
 * No worker accesses these pointers and no guessed destructor is invoked. */
static SzeroNativeSessionStage provider_quarantined_stage;
static SzeroNativeSessionHost provider_quarantined_host;
static SzeroNativeSessionCallbacks provider_quarantined_callbacks;
static void provider_quarantine_pair(void *context,const uintptr_t pair[2]) {
 if(InterlockedCompareExchange(&provider_stopped,1,0)!=0) return;
 if(context) provider_quarantined_host=*(SzeroNativeSessionHost *)context;
 provider_quarantined_stage.handle.tag=2;
 provider_quarantined_stage.handle.payload[0]=pair[0];
 provider_quarantined_stage.handle.payload[1]=pair[1];
 InterlockedExchange(&provider_native_stage,NATIVE_QUARANTINED);
 ipc_fail(IPC_SERVER_REJECTED,SZERO_ADAPTER_NATIVE_LAYOUT);
}
static void provider_quarantine_stage(SzeroNativeSessionStage *stage,
 const SzeroNativeSessionHost *host,const SzeroNativeSessionCallbacks *callbacks) {
 if(InterlockedCompareExchange(&provider_stopped,1,0)==0) {
  provider_quarantined_stage=*stage;
  provider_quarantined_host=*host;
  provider_quarantined_callbacks=*callbacks;
  provider_quarantined_callbacks.context=&provider_quarantined_host;
  provider_quarantined_callbacks.stream=NULL;
  memset(stage,0,sizeof(*stage));
 }
 ipc_fail(IPC_SERVER_REJECTED,SZERO_ADAPTER_NOT_READY);
 InterlockedExchange(&provider_native_stage,NATIVE_QUARANTINED);
}
static int provider_host(uintptr_t service,SzeroStreamWire *stream,
 SzeroNativeSessionHost *host,SzeroNativeSessionCallbacks *cb) {
 if(InterlockedCompareExchange(&provider_stopped,0,0)) return 0;
#ifdef SZERO_NATIVE_SESSION_IPC_TEST
 int valid=fixture_provider_host(service,stream,host,cb);
#else
 uintptr_t vt=0;if(!read_mem(service,&vt,8)) return 0;
 memset(host,0,sizeof(*host));host->image_base=base;host->service=service;
 host->expected_vptr=vt;host->native_thread_id=game_thread;
 host->bindings_verified=InterlockedCompareExchange(&verification,0,0)==2;
 host->owns_vptr=provider_owns;
 int valid=szero_native_session_host_bind(host,stream,cb) && szero_native_session_host_ready(host);
#endif
 if(valid) cb->quarantine_pair=provider_quarantine_pair;
 return valid;
}
static void *session_bind(void *self,void *out) {
 SzeroNativeSessionHost host;SzeroNativeSessionCallbacks cb;
 char address[32];int n=snprintf(address,sizeof(address),"127.0.0.1:%u",session_job.game_port);
 if(!provider_native_thread() || !session_job.game_port || n<=0 ||
  (size_t)n>=sizeof(address) || !provider_host((uintptr_t)self,NULL,&host,&cb)) {
  /* Same empty native string as the original base bind-address getter. */
  memset(out,0,sizeof(SzeroNativeString));return out;
 }
 memset(out,0,sizeof(SzeroNativeString));
 SzeroText text={(const unsigned char *)address,(size_t)n};
 cb.copy_string(cb.context,out,text);return out;
}
static void *provider_allocate(void *context,size_t bytes,size_t alignment) {
#ifdef SZERO_NATIVE_SESSION_IPC_TEST
 (void)context;(void)alignment;return calloc(1,bytes);
#else
 SzeroNativeSessionHost *host=context;uintptr_t allocator=0,vt=0,target=0;
 MEMORY_BASIC_INFORMATION info;
 if(!szero_native_session_host_ready(host) || !read_mem(base+szero_bind_rva(0x8cf7900),&allocator,8) ||
  !read_mem(allocator,&vt,8) || !read_mem(vt+0x20,&target,8) ||
  !VirtualQuery((void *)target,&info,sizeof(info)) || info.State!=MEM_COMMIT ||
  info.Type!=MEM_IMAGE || (uintptr_t)info.AllocationBase!=base ||
  (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) ||
  !((info.Protect&0xff)==PAGE_EXECUTE || (info.Protect&0xff)==PAGE_EXECUTE_READ ||
    (info.Protect&0xff)==PAGE_EXECUTE_READWRITE || (info.Protect&0xff)==PAGE_EXECUTE_WRITECOPY)) return NULL;
 typedef void *(SZERO_NATIVE_CALL *Fn)(uintptr_t,size_t,size_t);
 return ((Fn)target)(allocator,bytes,alignment);
#endif
}
static int provider_proxy_port(SzeroText address,unsigned *out) {
 if(address.size<11 || address.size>15 || !address.data ||
    memcmp(address.data,"127.0.0.1:",10) || address.data[10]<'1' || address.data[10]>'9')return 0;
 unsigned port=0;
 for(size_t i=10;i<address.size;i++) {
  if(address.data[i]<'0'||address.data[i]>'9')return 0;
  port=port*10u+(unsigned)(address.data[i]-'0');if(port>65535)return 0;
 }
 for(unsigned i=0;i<native_lan_proxy_count;i++)if(native_lan_proxy_ports[i]==port){*out=port;return 1;}
 return 0;
}
static int provider_addresses(SzeroSessionCodec *codec,uintptr_t service) {
 SzeroIdentityWire *identity=calloc(1,sizeof(*identity));
 if(!identity) return 0;
 int ok=provider_identity(service,identity);
 if(ok && native_lan_profile) {
  ok=InterlockedCompareExchange(&native_lan_identity_state,0,0)==1 &&
   szero_lan_identity_project(codec,(const unsigned char *)native_lan_primary,38,
    identity,session_job.kind==3?0:1);
 }
 if(!ok) {free(identity);return 0;}
 for(size_t i=0;i<codec->data.member_count;i++) {
  SzeroMemberData *member=&codec->members[i];
  int own=member->identity[0].size==identity->value[0].size &&
   member->identity[1].size==identity->value[1].size &&
   !memcmp(member->identity[0].data,identity->value[0].bytes,member->identity[0].size) &&
   !memcmp(member->identity[1].data,identity->value[1].bytes,member->identity[1].size);
  unsigned port=own?session_job.game_port:session_job.proxy_port;
  if(native_lan_multi && !own) {
   if(!provider_proxy_port(member->address,&port)) {free(identity);return 0;}
   for(size_t j=0;j<i;j++) if(member->address.size==codec->members[j].address.size &&
      !memcmp(member->address.data,codec->members[j].address.data,member->address.size)) {free(identity);return 0;}
  }
  int n=snprintf((char *)codec->storage[i].address,sizeof(codec->storage[i].address),
   "127.0.0.1:%u",port);
  if(n<=0 || (size_t)n>=sizeof(codec->storage[i].address)) {free(identity);return 0;}
  member->address.data=codec->storage[i].address;member->address.size=(size_t)n;
  codec->storage[i].address_size=(size_t)n;
 }
 free(identity);
 if(native_lan_profile) userinfo_observe(service,codec);
 return 1;
}
static int provider_decode(const char *frame,SzeroSessionCodec *codec) {
 if(strncmp(frame,native_lan_multi?"SESSION4 ":"SESSION3 ",9))return SZERO_SESSION_CODEC_INVALID;
 return szero_session_decode((const unsigned char *)frame,strlen(frame),codec);
}
static int provider_stats_writable(const void *stats) {
 if(!stats) return 1; /* Original local search explicitly permits NULL. */
 uintptr_t p=(uintptr_t)stats;MEMORY_BASIC_INFORMATION info;
 if(p>UINTPTR_MAX-24 || !VirtualQuery(stats,&info,sizeof(info)) || info.State!=MEM_COMMIT ||
  (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) || p<(uintptr_t)info.BaseAddress ||
  info.RegionSize<24 || p-(uintptr_t)info.BaseAddress>info.RegionSize-24) return 0;
 DWORD protection=info.Protect&0xff;
 return protection==PAGE_READWRITE || protection==PAGE_WRITECOPY ||
  protection==PAGE_EXECUTE_READWRITE || protection==PAGE_EXECUTE_WRITECOPY;
}
static void provider_stats_complete(void *stats,const uint64_t counts[2],int nonempty) {
 if(!stats) return;
 /* Recovered fields only. Our profile's finite result capacity is1. */
 *(unsigned char *)stats=(unsigned char)(nonempty!=0);
 memcpy((char *)stats+8,&counts[0],8);memcpy((char *)stats+16,&counts[1],8);
}
static void *session_operation(void *self,void *out,const void *input,
 const void *extra,uint16_t flags,int kind) {
 int tagged=kind!=2;
 InterlockedExchange(&provider_operation,kind);
 if(!provider_native_thread() || InterlockedCompareExchange(&provider_stopped,0,0)) return unavailable(out,tagged);
 void *task=current_task();
 if(!task) {provider_telemetry(kind,NATIVE_FAILED,SZERO_ADAPTER_NOT_READY);return unavailable(out,tagged);}
 if(!lifecycle_wait_background(task,out,tagged)) return out;
 if(InterlockedCompareExchange(&job.state,-1,0)!=0) {
  provider_telemetry(kind,NATIVE_FAILED,SZERO_ADAPTER_NOT_READY);return unavailable(out,tagged);
 }
 LONG id=InterlockedIncrement(&sequence);
 if(id<=0 || !provider_request((uintptr_t)self,input,extra,flags,kind,id)) {
  provider_telemetry(kind,NATIVE_CAPTURE_REFUSED,SZERO_ADAPTER_INVALID);
  ipc_fail(kind==3?IPC_QUERY_INVALID:IPC_CAPTURE_INVALID,0);InterlockedExchange(&job.state,0);return unavailable(out,tagged);
 }
 uint64_t stats_counts[2]={0};
 if(kind==3) {
  unsigned char captured[0x38];
  if(!read_mem((uintptr_t)input,captured,sizeof(captured)) || !provider_stats_writable(extra)) {
   provider_capture_fail(CAPTURE_STATS,0);
   provider_telemetry(kind,NATIVE_CAPTURE_REFUSED,SZERO_ADAPTER_INVALID);
   InterlockedExchange(&job.state,0);return unavailable(out,tagged);
  }
  stats_counts[0]=qword(captured+0x10);stats_counts[1]=qword(captured+0x30);
  if(stats_counts[0]>16 || stats_counts[1]>16) {
   InterlockedExchange(&job.state,0);return unavailable(out,tagged);
  }
 }
 SzeroSessionCodec *codec=calloc(1,sizeof(*codec));
 if(!codec) {InterlockedExchange(&job.state,0);return unavailable(out,tagged);}
 job.id=id;job.cancel=0;job.hook_done=0;session_job.kind=kind;session_job.empty=0;
 if(kind==3) {
  InterlockedExchange(&provider_search_request,id);
  InterlockedExchange(&provider_search_return_count,-1);
  InterlockedExchange(&provider_search_return_result,-1);
  InterlockedExchange(&provider_copy_mask,-1);
  InterlockedExchange(&provider_numeric_pass,-1);
  InterlockedExchange(&provider_self_exclusion,-1);
  InterlockedExchange(&provider_inspection_read,0);
 }
 if(kind==3) InterlockedIncrement(&searches);else if(kind==2) InterlockedIncrement(&joins);else InterlockedIncrement(&creates);
 SzeroNativeSessionStage stage={0};SzeroNativeResult error={0};
 SzeroNativeSessionCallbacks cb={0};SzeroNativeSessionHost host={0};
 int prepared=0,complete=0;ULONGLONG started=GetTickCount64();
 provider_telemetry(kind,NATIVE_WAITING,0);
 InterlockedExchange(&job.state,1);
 for(;;) {
  if(yield_cancel(task)) {
   InterlockedExchange(&job.cancel,1);InterlockedIncrement(&cancels);
   memset(out,0,tagged?48:40);copy_error((char *)out+(tagged?8:0),(char *)task+0x58);
   if(tagged) *(uint32_t *)out=1;
   break;
  }
  LONG state=InterlockedCompareExchange(&job.state,0,0);
  if(state==2 || GetTickCount64()-started>30000) {
   if(state!=2) ipc_fail(IPC_TIMEOUT,0);
   InterlockedExchange(&job.cancel,1);unavailable(out,tagged);break;
  }
  if(state==3 && !prepared) {
   int rc=SZERO_ADAPTER_INVALID;
   if((session_job.empty || provider_decode(session_job.frame,codec)==SZERO_SESSION_CODEC_OK) &&
      (session_job.empty || provider_addresses(codec,(uintptr_t)self)) &&
      provider_host((uintptr_t)self,&codec->stream,&host,&cb)) {
    if(kind==3) {
     /* Validate before native allocation. This is the suspended caller's own
      * output, never a worker pointer or cross-frame UObject wrapper. */
     if(!provider_stats_writable(extra)) {
      unavailable(out,tagged);InterlockedExchange(&job.cancel,1);complete=1;break;
     }
     SzeroNativeSearchCallbacks search_cb={0};search_cb.session=cb;search_cb.allocate_vector=provider_allocate;
     rc=szero_native_session_search(&search_cb,session_job.empty?NULL:&codec->data,session_job.empty?0:1,&error);
     InterlockedExchange(&provider_search_return_result,rc);
     InterlockedExchange(&provider_search_return_count,rc==SZERO_ADAPTER_OK?!session_job.empty:-1);
     if(rc==SZERO_ADAPTER_OK && !session_job.empty) {
      /* Inspect the actual deep-owned vector element, not the source DTO.
       * Read-only scalar diagnostics NEVER alter admission or the result. */
      SzeroSessionInspection inspection;unsigned normalize=0;
      SzeroIdentityWire *identity=calloc(1,sizeof(*identity));
      int have_identity=identity && provider_identity((uintptr_t)self,identity);
      if(provider_default_normalize((uintptr_t)self,&normalize)) {
       szero_native_session_inspect(error.payload[0],(uintptr_t)input,&codec->data,
        have_identity?identity->value:NULL,(int)normalize,provider_read,NULL,&inspection);
       InterlockedExchange(&provider_copy_mask,inspection.copy_mask);
       InterlockedExchange(&provider_numeric_pass,inspection.numeric_pass);
       InterlockedExchange(&provider_self_exclusion,inspection.self_exclusion);
       InterlockedExchange(&provider_inspection_read,inspection.read_ok);
      }
      free(identity);
     }
     if(rc==SZERO_ADAPTER_OK) provider_stats_complete((void *)extra,stats_counts,!session_job.empty);
     if(!InterlockedCompareExchange(&provider_stopped,0,0))
      provider_telemetry(kind,rc==SZERO_ADAPTER_OK?NATIVE_SEARCH_RETURNED:NATIVE_FAILED,rc);
     if(rc==SZERO_ADAPTER_OK || rc==SZERO_ADAPTER_NATIVE_ERROR) {memcpy(out,&error,48);complete=1;}
     break;
    }
    rc=szero_native_session_prepare(&cb,&codec->data,kind!=2,&stage,&error);
   }
   if(rc!=SZERO_ADAPTER_OK) {
    if(!InterlockedCompareExchange(&provider_stopped,0,0)) provider_telemetry(kind,NATIVE_FAILED,rc);
    if(rc==SZERO_ADAPTER_NATIVE_ERROR) {
     if(tagged) memcpy(out,&error,48);else memcpy(out,error.payload,40);
    } else unavailable(out,tagged);
    InterlockedExchange(&job.cancel,1);complete=1;break;
   }
   provider_telemetry(kind,NATIVE_PREPARED,rc);prepared=1;InterlockedExchange(&job.state,4);
  }
  if(state==5 && prepared) {
   memset(out,0,tagged?48:40);
   provider_telemetry(kind,NATIVE_SERVER_COMMITTED,0);
   int rc=szero_native_session_commit(&cb,&stage,out);
   provider_telemetry(kind,rc==SZERO_ADAPTER_OK?NATIVE_CACHED:NATIVE_FAILED,rc);
   if(rc==SZERO_ADAPTER_OK) provider_frame_mark((uintptr_t)self,session_job.frame);
   if(rc!=SZERO_ADAPTER_OK) {
    unavailable(out,tagged);InterlockedExchange(&job.cancel,1);
   }
   complete=1;break;
  }
 }
 if(!complete && !InterlockedCompareExchange(&job.cancel,0,0)) {
  unavailable(out,tagged);InterlockedExchange(&job.cancel,1);
 }
 if(stage.state==SZERO_STAGE_PREPARED && szero_native_session_abort(&cb,&stage)!=SZERO_ADAPTER_OK)
  provider_quarantine_stage(&stage,&host,&cb);
 free(codec);InterlockedExchange(&job.hook_done,1);return out;
}
static void process_session_job(void) {
 InterlockedExchange(&last_request,job.id);InterlockedExchange(&ipc_error,IPC_OK);
 InterlockedExchange(&ipc_error_code,0);
 SOCKET socket=connect_bridge();char line[128],expected[128];int mutation=0,committed=0;
 InterlockedExchange(&ipc_phase,IPC_BEGIN);
 if(socket==INVALID_SOCKET || !send_line(socket,job.begin) || !receive_line(socket,line,sizeof(line))) goto failed;
 snprintf(expected,sizeof(expected),"RESULT3 %ld PREPARED\n",job.id);
 if(!strcmp(line,expected)) mutation=1;
 else {
  snprintf(expected,sizeof(expected),"RESULT3 %ld EMPTY\n",job.id);
  if(!strcmp(line,expected) && (session_job.kind==3 || session_job.kind==7)) session_job.empty=1;
  else {snprintf(expected,sizeof(expected),"RESULT3 %ld OK\n",job.id);
   if(strcmp(line,expected) || (session_job.kind!=3 && session_job.kind<5)) goto failed;}
 }
 if(!session_job.empty && session_job.kind!=6 &&
    !receive_line(socket,session_job.frame,sizeof(session_job.frame))) goto failed;
 InterlockedExchange(&job.state,3);
 InterlockedExchange(&ipc_phase,IPC_PENDING);
 while(!InterlockedCompareExchange(&job.hook_done,0,0) && !InterlockedCompareExchange(&job.cancel,0,0)) {
  if(mutation && !committed && InterlockedCompareExchange(&job.state,0,0)==4) {
   snprintf(line,sizeof(line),"ACK3 %ld\n",job.id);
   snprintf(expected,sizeof(expected),"RESULT3 %ld COMMITTED\n",job.id);
   if(!send_line(socket,line) || !receive_line(socket,line,sizeof(line)) || strcmp(line,expected)) goto failed;
   committed=1;InterlockedExchange(&job.state,5);
  }
  Sleep(10);
 }
 goto cleanup;
failed:
 ipc_fail(IPC_SERVER_REJECTED,0);InterlockedExchange(&job.state,2);
cleanup:
 if(socket!=INVALID_SOCKET) {
  if(InterlockedCompareExchange(&job.cancel,0,0) || (mutation && !committed)) {
   snprintf(line,sizeof(line),"CANCEL3 %ld\n",job.id);send_line(socket,line);
  }
  closesocket(socket);
 }
 while(!InterlockedCompareExchange(&job.hook_done,0,0)) Sleep(10);
 InterlockedExchange(&job.state,0);
 if(InterlockedCompareExchange(&ipc_error,0,0)==IPC_OK) InterlockedExchange(&ipc_phase,IPC_CLOSED);
}
