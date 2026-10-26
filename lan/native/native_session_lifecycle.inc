/* Included after provider.inc's dispatcher helpers. No socket work runs here.
 * Unsupported ownership-bearing settings are rejected, never silently lost.
 * These developer callbacks do not replace platform readiness/authentication. */
static uintptr_t lifecycle_original(uintptr_t service,unsigned slot) {
 for(unsigned i=0;i<replacement_count;i++) if(replacements[i].object==service) {
  uintptr_t target=0;
  if(slot>=28 || !read_mem(replacements[i].original+slot*8,&target,8)) return 0;
  return target;
 }
 return 0;
}
static int lifecycle_executable(uintptr_t target) {
 MEMORY_BASIC_INFORMATION info;
 if(!target || !VirtualQuery((void *)target,&info,sizeof(info)) ||
    info.State!=MEM_COMMIT || info.Type!=MEM_IMAGE ||
    (uintptr_t)info.AllocationBase!=base || (info.Protect&(PAGE_NOACCESS|PAGE_GUARD))) return 0;
 DWORD p=info.Protect&0xff;
 return p==PAGE_EXECUTE || p==PAGE_EXECUTE_READ || p==PAGE_EXECUTE_READWRITE || p==PAGE_EXECUTE_WRITECOPY;
}
static void *lifecycle_readiness(void *self,void *out) {
 /* Service+c8 is NOT a portable status getter: Steam145927dc0 consumes
  * two additional ID views. Calling it with two arguments caused the supplied
  * Windows null-read dump. Follow LOCAL14592efa0's actual platform getter:
  * service+8 -> bundle; bundle+8 -> platform; platform virtual+60.
  * Preserve the real platform result, never manufacture readiness. */
 uintptr_t owned=0,bundle=0,platform=0,vt=0,target=0;
 if(!provider_native_thread() ||
    !read_mem((uintptr_t)self,&owned,8) || !provider_owns(NULL,(uintptr_t)self,owned) ||
    !read_mem((uintptr_t)self+8,&bundle,8) || !bundle ||
    !read_mem(bundle+8,&platform,8) || !platform ||
    !read_mem(platform,&vt,8) || !vt ||
    !read_mem(vt+0x60,&target,8) || !lifecycle_executable(target)) return unavailable(out,0);
 typedef void *(SZERO_NATIVE_CALL *Fn)(void *,void *);
 return ((Fn)target)((void *)platform,out);
}
static void *lifecycle_platform_operation(void *self,void *out,const void *first,const void *second) {
 /* Steam+c8's four-argument operation is not the LOCAL status method.
  * Its LAN equivalent is unsupported. Do not call production Steam or return
  * a fabricated successful status for that request. */
 (void)self;(void)first;(void)second;
 return unavailable(out,0);
}
static int lifecycle_active_id(uintptr_t service,unsigned char id[32]) {
 uintptr_t descriptor=0;uint64_t words[4];
 if(!read_mem(service+0x218,&descriptor,8) || !descriptor ||
    !read_mem(descriptor,words,sizeof(words))) return 0;
 size_t size=(words[0]&1)?(size_t)words[2]:(size_t)(((unsigned char *)words)[0]>>2);
 uintptr_t text=(words[0]&1)?(uintptr_t)words[1]:descriptor+1;
 if(size!=32 || !read_mem(text,id,32)) return 0;
 for(unsigned i=0;i<32;i++) if(!((id[i]>='0'&&id[i]<='9')||(id[i]>='a'&&id[i]<='f'))) return 0;
 return 1;
}
static int lifecycle_id_matches(uintptr_t service,const void *view) {
 unsigned char active[32],supplied[32];uintptr_t pair[2];
 return lifecycle_active_id(service,active) && read_mem((uintptr_t)view,pair,sizeof(pair)) &&
  pair[1]==32 && read_mem(pair[0],supplied,32) && !memcmp(active,supplied,32);
}
static int lifecycle_descriptor_matches(uintptr_t service,const SzeroSessionCodec *codec) {
 uintptr_t view[2]={(uintptr_t)codec->data.id.data,codec->data.id.size};
 return lifecycle_id_matches(service,view);
}
static int lifecycle_applied_same(uintptr_t service,const char *frame) {
 /* The cached frame was fully decoded before marking. Still check the native
  * cache's current ID before skipping, not just its service-instance pointer. */
 if(!provider_frame_same(service,frame) || provider_frame_size(frame)<42 ||
    memcmp(frame,native_lan_multi?"SESSION4 ":"SESSION3 ",9)) return 0;
 uintptr_t view[2]={(uintptr_t)(frame+9),32};
 return lifecycle_id_matches(service,view);
}
static int lifecycle_remove_cache(uintptr_t service,const unsigned char id[32]) {
#ifdef SZERO_NATIVE_SESSION_LIFECYCLE_TEST
 int removed=fixture_lifecycle_remove_cache(service,id);
 if(removed) provider_frame_clear(service);
 return removed;
#else
 SzeroNativeSessionHost host;SzeroNativeSessionCallbacks cb;
 if(!provider_host(service,NULL,&host,&cb) || !lifecycle_executable(base+0x58cbe10)) return 0;
 uintptr_t view[2]={(uintptr_t)id,32};SzeroNativeError reason={0};reason.code=0x57c3a7bb;
 typedef void (SZERO_NATIVE_CALL *Fn)(uintptr_t,const void *,const void *,unsigned char);
 ((Fn)(base+0x58cbe10))(service,view,&reason,0);
 provider_frame_clear(service);
 return 1;
#endif
}
static uintptr_t lifecycle_background_service;
static void lifecycle_finish_background(void) {
 if(InterlockedCompareExchange(&job.hook_done,0,0)) return;
 LONG state=InterlockedCompareExchange(&job.state,0,0);
 if(state!=2 && state!=3) return;
 if(state==3) {
  uintptr_t service=lifecycle_background_service;
  SzeroNativeSessionHost guard_host={0};SzeroNativeSessionCallbacks guard_cb={0};
  /* provider_host verifies current title context, selected service and owned
   * vptr. A delayed old-context snapshot never targets a replacement service. */
  if(provider_host(service,NULL,&guard_host,&guard_cb)) {
   if(session_job.empty) {
    unsigned char id[32];
    if(lifecycle_active_id(service,id)) lifecycle_remove_cache(service,id);
    else provider_frame_clear(service);
   } else if(!lifecycle_applied_same(service,session_job.frame)) {
    SzeroSessionCodec *codec=calloc(1,sizeof(*codec));
    SzeroNativeSessionHost host={0};SzeroNativeSessionCallbacks cb={0};
    if(codec && provider_decode(session_job.frame,codec)==SZERO_SESSION_CODEC_OK &&
       lifecycle_descriptor_matches(service,codec) &&
       provider_addresses(codec,service) && provider_host(service,&codec->stream,&host,&cb)) {
     SzeroNativeResult error={0};
     int rc=szero_native_session_refresh(&cb,&codec->data,&error);
     if(rc==SZERO_ADAPTER_OK) provider_frame_mark(service,session_job.frame);
     /* Native owned errors must not leak if a background update fails. */
     if(rc==SZERO_ADAPTER_NATIVE_ERROR && error.tag==1 && cb.destroy_string)
      cb.destroy_string(cb.context,(SzeroNativeString *)&error.payload[1]);
    }
    free(codec);
   }
  }
 }
 InterlockedExchange(&job.hook_done,1);
}
static int lifecycle_wait_background(void *task,void *out,int tagged) {
 if(!provider_native_thread() || !task) {unavailable(out,tagged);return 0;}
 ULONGLONG started=GetTickCount64();
 for(;;) {
  LONG background=InterlockedCompareExchange(&session_job.background,0,0);
  LONG state=InterlockedCompareExchange(&job.state,0,0);
  if(state==0) {
   if(background) InterlockedExchange(&session_job.background,0);
   return 1;
  }
  /* A completed foreground hook still owns the mailbox until the worker has
   * closed its IPC operation and recycled state0. Cooperatively drain that
   * handoff; never reject the immediately following native operation merely
   * because its predecessor has returned a few milliseconds earlier. */
  if(background) lifecycle_finish_background();
  else if(!InterlockedCompareExchange(&job.hook_done,0,0)) {
   unavailable(out,tagged);return 0; /* Truly ongoing operation, not a fence. */
  }
  if(yield_cancel(task)) {
   memset(out,0,tagged?48:40);copy_error((char *)out+(tagged?8:0),(char *)task+0x58);
   if(tagged) *(uint32_t *)out=1;
   return 0;
  }
  if(GetTickCount64()-started>30000) {
   /* Never cancel a completed foreground transaction while waiting to start
    * its successor: that could revoke the already accepted session. */
   if(background) InterlockedExchange(&job.cancel,1);
   unavailable(out,tagged);return 0;
  }
 }
}
static int lifecycle_drain_native_queue(void *self) {
 uintptr_t vptr=0;
 /* This forwards original +38 work on its original calling thread. Do not
  * require our unproven Lua-thread identity to preserve native completions.
  * Only LAN-specific work below is restricted to the recorded thread. */
 if(InterlockedCompareExchange(&verification,0,0)!=2 ||
    !read_mem((uintptr_t)self,&vptr,8) || !provider_owns(NULL,(uintptr_t)self,vptr)) return 0;
#ifdef SZERO_NATIVE_SESSION_LIFECYCLE_TEST
 fixture_lifecycle_base_tick(self);
#else
 /* Exact original Steam+38 thunk1458cec20 adds service+228 and tailcalls
  * generic locked task-queue14582e450. It does NOT dispatch Steam sessions.
  * Preserve this common base queue for every owned provider, not the LOCAL
  * registry-specific tick14592f6f0 which cannot interpret central LAN IDs. */
 if(!lifecycle_executable(base+0x58cec20)) return 0;
 typedef void (SZERO_NATIVE_CALL *Tick)(void *);
 ((Tick)(base+0x58cec20))(self);
#endif
 return 1;
}
static void lifecycle_tick(void *self) {
 static ULONGLONG last_poll;
 /* Native task completions must progress even while our mailbox is busy,
  * polling is rate-limited, or no active session exists. Never move this
  * after any of those early returns. Original queue forwarding remains on
  * its caller's thread; wrong-thread LAN calls are reported and refused. */
 if(!lifecycle_drain_native_queue(self)) return;
 if(!provider_native_thread()) return;
 if(InterlockedCompareExchange(&session_job.background,0,0)) {
  if(InterlockedCompareExchange(&job.state,0,0)!=0) {
   lifecycle_finish_background();return;
  }
  InterlockedExchange(&session_job.background,0);
 }
 unsigned char active[32];ULONGLONG now=GetTickCount64();
 if(now-last_poll<1000 || !lifecycle_active_id((uintptr_t)self,active)) return;
 SzeroNativeSessionHost host={0};SzeroNativeSessionCallbacks cb={0};
 if(!provider_host((uintptr_t)self,NULL,&host,&cb) ||
    InterlockedCompareExchange(&job.state,-1,0)!=0) return;
 LONG id=InterlockedIncrement(&sequence);size_t used=0;
 if(id<=0 || !append(job.begin,&used,"POLL3 %ld\n",id)) {
  InterlockedExchange(&job.state,0);return;
 }
 job.id=id;job.cancel=0;job.hook_done=0;session_job.kind=7;session_job.empty=0;
 lifecycle_background_service=(uintptr_t)self;
 last_poll=now;InterlockedExchange(&session_job.background,1);InterlockedExchange(&job.state,1);
}
/* Plain40 error ABI. kind5 flags,6leave,7finite membership snapshot,8member.
 * Worker owns IPC. On success5/7/8 descriptor is deep-owned diff input and
 * consumed through the original in-place native update, never node swapping. */
static int lifecycle_settings_request(uintptr_t service,const void *input,LONG id) {
 SzeroIdentityWire identity;SzeroMemberWire member;uintptr_t descriptor=0;
 unsigned char field_e1=0;
 SzeroSettingsWire *settings=calloc(1,sizeof(*settings));size_t used=0;
 if(!settings) return 0;
 int ok=provider_identity(service,&identity) && read_mem(service+0x218,&descriptor,8) &&
  read_mem(descriptor+0xe1,&field_e1,1) &&
  szero_capture_local_member(descriptor,&identity,provider_read,NULL,&member)==SZERO_WIRE_OK &&
  szero_capture_settings((uintptr_t)input,base,provider_read,NULL,settings)==SZERO_WIRE_OK &&
  settings->numeric_count<=16 && settings->capacity>=1 &&
  settings->capacity<=(native_lan_multi?SZERO_MATERIALIZER_MAX_MEMBERS:2) &&
  (native_lan_multi || settings->capacity==2) &&
  append(job.begin,&used,"UPDATESETTINGS3 %ld %lu %llu",id,
   (unsigned long)settings->compatibility,(unsigned long long)settings->numeric_count);
 for(size_t i=0;ok && i<settings->numeric_count;i++) ok=append(job.begin,&used," %ld",(long)settings->numeric[i]);
 if(ok) ok=append(job.begin,&used," %u %u %u %llu %llu %llu ",settings->capacity,field_e1,settings->stream.present,
  (unsigned long long)settings->stream.size,(unsigned long long)settings->stream.read_cursor,
  (unsigned long long)settings->stream.write_cursor) &&
  provider_hex(job.begin,&used,settings->stream.bytes,(size_t)settings->stream.size) && append(job.begin,&used," ") &&
  provider_hex(job.begin,&used,identity.value[0].bytes,(size_t)identity.value[0].size) && append(job.begin,&used," ") &&
  provider_hex(job.begin,&used,identity.value[1].bytes,(size_t)identity.value[1].size) && append(job.begin,&used," ") &&
  provider_hex(job.begin,&used,member.address.bytes,(size_t)member.address.size) &&
  append(job.begin,&used," %u %u %u\n",member.field_88,member.optional_present,member.optional_value);
 free(settings);return ok;
}
static void *lifecycle_control(void *self,void *out,int kind,uint16_t flags,const void *settings) {
 void *task=current_task();
 if(!provider_native_thread() || !task) return unavailable(out,0);
 if(!lifecycle_wait_background(task,out,0)) return out;
 if(InterlockedCompareExchange(&job.state,-1,0)!=0) return unavailable(out,0);
 LONG id=InterlockedIncrement(&sequence);size_t used=0;
 SzeroNativeSessionHost host={0};SzeroNativeSessionCallbacks cb={0};
 if(id<=0 || !provider_host((uintptr_t)self,NULL,&host,&cb)) {
  InterlockedExchange(&job.state,0);return unavailable(out,0);
 }
 int valid=kind==8?lifecycle_settings_request((uintptr_t)self,settings,id):
  kind==5?append(job.begin,&used,"FLAGS3 %ld %u\n",id,flags):
  append(job.begin,&used,"%s %ld\n",kind==6?"LEAVE3":"POLL3",id);
 if(!valid) {InterlockedExchange(&job.state,0);return unavailable(out,0);}
 SzeroSessionCodec *codec=calloc(1,sizeof(*codec));
 if(!codec) {InterlockedExchange(&job.state,0);return unavailable(out,0);}
 job.id=id;job.cancel=0;job.hook_done=0;session_job.kind=kind;session_job.empty=0;
 InterlockedExchange(&job.state,1);ULONGLONG started=GetTickCount64();
 int done=0;
 for(;;) {
  if(yield_cancel(task)) {
   InterlockedExchange(&job.cancel,1);memset(out,0,40);copy_error(out,(char *)task+0x58);done=1;break;
  }
  LONG state=InterlockedCompareExchange(&job.state,0,0);
  if(state==2 || GetTickCount64()-started>30000) {InterlockedExchange(&job.cancel,1);break;}
  if(state==3) {
   if(kind==6) {memset(out,0,40);done=1;break;}
   if(session_job.empty) break; /* No invented membership/fence success. */
   if((kind==5 || kind==7) && lifecycle_applied_same((uintptr_t)self,session_job.frame)) {
    if(!provider_host((uintptr_t)self,NULL,&host,&cb)) break;
    memset(out,0,40);done=1;break;
   }
   if(provider_decode(session_job.frame,codec)!=SZERO_SESSION_CODEC_OK ||
      !lifecycle_descriptor_matches((uintptr_t)self,codec) ||
      !provider_addresses(codec,(uintptr_t)self) ||
      !provider_host((uintptr_t)self,&codec->stream,&host,&cb)) break;
   SzeroNativeResult error={0};
   int rc=szero_native_session_refresh(&cb,&codec->data,&error);
   if(rc==SZERO_ADAPTER_OK) {
    provider_frame_mark((uintptr_t)self,session_job.frame);memset(out,0,40);done=1;
   }
   else if(rc==SZERO_ADAPTER_NATIVE_ERROR) {memcpy(out,error.payload,40);done=1;}
   break;
  }
 }
 if(!done) unavailable(out,0);
 free(codec);InterlockedExchange(&job.hook_done,1);return out;
}
static void *lifecycle_match(void *self,void *out,const void *settings,const void *query,uint16_t flags) {
 SzeroNativeError readiness={0};lifecycle_readiness(self,&readiness);
 if((readiness.code&0xffffff00)!=0) {
  memset(out,0,48);*(uint32_t *)out=1;memcpy((char *)out+8,&readiness,40);return out;
 }
 /* Capture copies values; ownership of the input never moves into our hook.
  * Original LOCAL moves because its registry takes ownership. The default
  * Steam+a0 returns unsupported without consuming the argument at all. */
 return session_operation(self,out,settings,query,flags,4);
}
static void *lifecycle_create(void *self,void *out,const void *settings,uint16_t flags) {
 SzeroNativeError readiness={0};lifecycle_readiness(self,&readiness);
 if((readiness.code&0xffffff00)!=0) {
  memset(out,0,48);*(uint32_t *)out=1;memcpy((char *)out+8,&readiness,40);return out;
 }
 /* +88 is called by1458c84a0, which ALWAYS destroys the caller's settings
  * after this virtual returns, including errors. Unlike original LOCALcreate
  * we copy values, never move ownership into a registry. Leave the entire
  * borrowed object untouched: no speculative destructor after refused capture.
  * See analysis/native-session-service-virtual-boundary.txt. */
 return session_operation(self,out,settings,NULL,flags,1);
}
static void *lifecycle_flags(void *self,void *out,const void *view,uint16_t flags) {
 if(!lifecycle_id_matches((uintptr_t)self,view)) return unavailable(out,0);
 return lifecycle_control(self,out,5,flags,NULL);
}
static void *lifecycle_leave(void *self,void *out,const void *view) {
 unsigned char id[32];
 if(!lifecycle_id_matches((uintptr_t)self,view) || !lifecycle_active_id((uintptr_t)self,id)) return unavailable(out,1);
 SzeroNativeError result={0};lifecycle_control(self,&result,6,0,NULL);
 if((result.code&0xffffff00)!=0) {
  memset(out,0,48);*(uint32_t *)out=1;memcpy((char *)out+8,&result,40);return out;
 }
 if(!lifecycle_remove_cache((uintptr_t)self,id)) return unavailable(out,1);
 memset(&result,0,sizeof(result));lifecycle_readiness(self,&result);
 memset(out,0,48);*(uint32_t *)out=2;memcpy((char *)out+8,&result,40);return out;
}
static void *lifecycle_fence(void *self,void *out,const void *view) {
 /* Original+d0 argument is opaque task/fence data, NOT a proven ID view.
  * Never interpret/dereference it as a session identifier. */
 (void)view;unsigned char id[32];void *task=current_task();
 if(!lifecycle_wait_background(task,out,0)) return out;
 if(!lifecycle_active_id((uintptr_t)self,id)) return lifecycle_readiness(self,out);
 lifecycle_control(self,out,7,0,NULL);
 if((*(uint32_t *)out&0xffffff00)!=0) return out;
 return lifecycle_readiness(self,out);
}
static void *lifecycle_settings(void *self,void *out,const void *view,const void *optional) {
 unsigned char present;
 if(!lifecycle_id_matches((uintptr_t)self,view) ||
    !read_mem((uintptr_t)optional,&present,1) || present>1) return unavailable(out,0);
 if(present) {
  lifecycle_readiness(self,out);
  if((*(uint32_t *)out&0xffffff00)!=0) return out;
  void *settings=(char *)optional+8;
  /* As with create, optional settings remain the original caller's property.
   * On readiness failure original LOCAL also leaves this object untouched. */
  return lifecycle_control(self,out,8,0,settings);
 }
 return lifecycle_readiness(self,out);
}
static void *lifecycle_teardown(void *self,void *out) {
 unsigned char id[32];uintptr_t descriptor=0;
 if(!provider_native_thread() || !read_mem((uintptr_t)self+0x218,&descriptor,8)) return unavailable(out,0);
 if(descriptor) {
  if(!lifecycle_active_id((uintptr_t)self,id)) return unavailable(out,0);
  lifecycle_control(self,out,6,0,NULL);
  if((*(uint32_t *)out&0xffffff00)!=0) return out;
  if(!lifecycle_remove_cache((uintptr_t)self,id)) return unavailable(out,0);
 }
 /* Original Steam +60 directly calls Steam leave rather than virtual+c0.
  * Do not call it until ALL cached descriptors are gone, not only active. */
 uint64_t cache_count=0;
 if(!read_mem((uintptr_t)self+0x200,&cache_count,8) || cache_count!=0) return unavailable(out,0);
 uintptr_t target=lifecycle_original((uintptr_t)self,12);
 if(!lifecycle_executable(target)) return unavailable(out,0);
 typedef void *(SZERO_NATIVE_CALL *Fn)(void *,void *);
 return ((Fn)target)(self,out);
}
