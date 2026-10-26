/* Included only in the exact-image native provider. A pinned immutable clone
 * changes only user+98 relationship metadata; all platform/auth/user identity
 * methods remain original. LAN authorization comes from validated directory
 * DTOs, never an arbitrary caller-supplied szlan: string. */
typedef struct {
 uintptr_t service;unsigned count;unsigned char principal[SZERO_MATERIALIZER_MAX_MEMBERS+1][38];
} UserInfoDirectoryView;
typedef struct {
 uintptr_t user,original,table[20];UserInfoDirectoryView views[4];
} UserInfoReplacement;
static UserInfoReplacement userinfo_replacements[4];
static volatile LONG userinfo_replacement_count;
static const uintptr_t userinfo_steam_slots[20]={
 0x58af690,0x20f8b70,0x58af4b0,0x58ae870,0x11072d0,0x58fa230,0x10fd050,
 0x58e0f90,0x58fa280,0x5842490,0x11072d0,0x58af000,0x58dfeb0,0x58fabf0,
 0x58de740,0x5842490,0x58fa630,0x58faba0,0x58fab50,0x58fa310};
static void *userinfo_hook(void *,void *,const void *,void *);
static int userinfo_service_user(uintptr_t service,uintptr_t *user) {
 uintptr_t vt=0,bundle=0;
 return read_mem(service,&vt,8) && provider_owns(NULL,service,vt) &&
  read_mem(service+8,&bundle,8) && bundle &&
  read_mem(bundle+0x18,user,8) && *user;
}
static UserInfoReplacement *userinfo_binding(uintptr_t user) {
 uintptr_t vt=0;
 if(!read_mem(user,&vt,8)) return NULL;
 for(LONG i=0;i<InterlockedCompareExchange(&userinfo_replacement_count,0,0);i++)
  if(userinfo_replacements[i].user==user &&
     vt==(uintptr_t)userinfo_replacements[i].table) return userinfo_replacements+i;
 return NULL;
}
static int userinfo_ready(void *context) {
 UserInfoReplacement *r=context;uintptr_t ctx=0,service=0,user=0;
 return native_lan_profile && session_v3 && verification==2 &&
  InterlockedCompareExchange(&native_lan_identity_state,0,0)==1 &&
  !InterlockedCompareExchange(&provider_stopped,0,0) &&
  GetCurrentThreadId()==game_thread && selected(&ctx,&service) &&
  userinfo_service_user(service,&user) && user==r->user && userinfo_binding(user)==r;
}
static int userinfo_known(void *context,const unsigned char principal[38]) {
 UserInfoReplacement *r=context;uintptr_t ctx=0,service=0;
 if(!selected(&ctx,&service)) return 0;
 for(unsigned i=0;i<4;i++) if(r->views[i].service==service)
  for(unsigned j=0;j<r->views[i].count;j++)
   if(!memcmp(r->views[i].principal[j],principal,38)) return 1;
 return 0;
}
static int userinfo_read(void *context,uintptr_t p,void *out,size_t n) {
 (void)context;return read_mem(p,out,n);
}
static int userinfo_writable(void *context,uintptr_t p,size_t n) {
 (void)context;
 if(!p || !n || n>UINTPTR_MAX-p) return 0;
 uintptr_t end=p+n;
 while(p<end) {
  MEMORY_BASIC_INFORMATION m;
  if(!VirtualQuery((void *)p,&m,sizeof(m)) || m.State!=MEM_COMMIT ||
     (m.Protect&(PAGE_GUARD|PAGE_NOACCESS)) || p<(uintptr_t)m.BaseAddress ||
     m.RegionSize>UINTPTR_MAX-(uintptr_t)m.BaseAddress) return 0;
  DWORD prot=m.Protect&0xff;
  if(prot!=PAGE_READWRITE && prot!=PAGE_WRITECOPY && prot!=PAGE_EXECUTE_READWRITE &&
     prot!=PAGE_EXECUTE_WRITECOPY) return 0;
  uintptr_t next=(uintptr_t)m.BaseAddress+m.RegionSize;
  if(next<=p) return 0;
  p=next<end?next:end;
 }
 return 1;
}
static void userinfo_write(void *context,uintptr_t p,const void *in,size_t n) {
 (void)context;memcpy((void *)p,in,n);
}
static int userinfo_copy_id(void *context,SzeroNativeString *out,const SzeroNativeString *in) {
 (void)context;
 if(!(in->words[0]&1)) {*out=*in;return 1;}
 uint64_t size=in->words[2];
 if(size>255 || size>in->words[3]) return 0;
 unsigned char *copy=calloc((size_t)size+1,1);if(!copy) return 0;
 if(size && !read_mem((uintptr_t)in->words[1],copy,(size_t)size)) {free(copy);return 0;}
 typedef void *(SZERO_NATIVE_CALL *Fn)(void *,const void *,size_t,size_t);
 ((Fn)(base+0x1dcc4a0))(out,copy,(size_t)size,(size_t)size);
 free(copy);return 1;
}
static void userinfo_destroy_id(void *context,SzeroNativeString *owned) {
 (void)context;
 if(owned->words[0]&1) {
  uintptr_t allocator=(uintptr_t)(owned->words[0]&~UINT64_C(3));
  if(!allocator) allocator=*(uintptr_t *)(base+0x8cf7900);
  typedef void (SZERO_NATIVE_CALL *Fn)(uintptr_t,uintptr_t);
  uintptr_t vt=*(uintptr_t *)allocator;
  ((Fn)(*(uintptr_t *)(vt+0x28)))(allocator,(uintptr_t)owned->words[1]);
 }
 memset(owned,0,sizeof(*owned));
}
static void *userinfo_original(void *context,void *self,void *out,const void *ids,void *records) {
 UserInfoReplacement *r=context;
 typedef void (SZERO_NATIVE_CALL *Fn)(void *,void *,const void *,void *);
 /* Immutable exact-slot validation at publication, no caller-supplied code. */
 ((Fn)(base+userinfo_steam_slots[19]))(self,out,ids,records);
 (void)r;return out;
}
static void *userinfo_hook(void *self,void *out,const void *ids,void *records) {
 UserInfoReplacement *r=userinfo_binding((uintptr_t)self);
 if(!r) return unavailable(out,1);
 SzeroUserInfoCallbacks cb={r,userinfo_read,userinfo_writable,userinfo_write,
  userinfo_ready,userinfo_known,userinfo_copy_id,userinfo_destroy_id,userinfo_original};
 if(!szero_lan_userinfo_dispatch(self,out,ids,records,&cb)) return unavailable(out,1);
 return out;
}
static UserInfoReplacement *userinfo_publish(uintptr_t service) {
 uintptr_t user=0,vt=0,ctx=0,current_service=0;uintptr_t original[20];
 if(!native_lan_profile || !session_v3 || verification!=2 ||
    GetCurrentThreadId()!=game_thread || !selected(&ctx,&current_service) ||
    current_service!=service || !userinfo_service_user(service,&user)) return NULL;
 UserInfoReplacement *existing=userinfo_binding(user);
 if(existing) return existing;
 /* Never recycle a published table, including a destroyed/reused object. */
 for(LONG i=0;i<InterlockedCompareExchange(&userinfo_replacement_count,0,0);i++) if(userinfo_replacements[i].user==user) return NULL;
 if(userinfo_replacement_count==4 || !writable_pointer(user) ||
    !read_mem(user,&vt,8) || vt!=base+0x7b94d68 ||
    !read_mem(vt,original,sizeof(original))) return NULL;
 for(unsigned i=0;i<20;i++) if(original[i]!=base+userinfo_steam_slots[i]) return NULL;
 UserInfoReplacement *r=userinfo_replacements+userinfo_replacement_count;
 memset(r,0,sizeof(*r));r->user=user;r->original=vt;memcpy(r->table,original,sizeof(original));
 r->table[19]=(uintptr_t)userinfo_hook;
 /* Make lookup visible before an arbitrary original native thread calls an
  * unchanged method through the newly published vptr. No existing work drops. */
 InterlockedIncrement(&userinfo_replacement_count);
 if((uintptr_t)InterlockedCompareExchangePointer((void *volatile *)user,r->table,(void *)vt)!=vt)
  return NULL;
 return r;
}
static int userinfo_service_ready(uintptr_t service) {
 uintptr_t user=0;if(!userinfo_service_user(service,&user)) return 0;
 UserInfoReplacement *r=userinfo_binding(user);
 if(!r || !userinfo_ready(r)) return 0;
 for(unsigned i=0;i<4;i++) if(r->views[i].service==service && r->views[i].count) return 1;
 return 0;
}
static void userinfo_clear(uintptr_t service) {
 for(LONG i=0;i<InterlockedCompareExchange(&userinfo_replacement_count,0,0);i++) for(unsigned j=0;j<4;j++)
  if(userinfo_replacements[i].views[j].service==service)
   memset(userinfo_replacements[i].views+j,0,sizeof(UserInfoDirectoryView));
}
static void userinfo_observe(uintptr_t service,const SzeroSessionCodec *codec) {
 /* Called ONLY after owned DTO validation and LAN projection succeeded.
  * Unknown user implementations remain untouched; Quickmatch keeps its old
  * path, while0x200 is not admitted without the vetted user adaptation. */
 UserInfoReplacement *r=userinfo_publish(service);if(!r) return;
 UserInfoDirectoryView view={0};view.service=service;
 for(size_t i=0;i<codec->data.member_count;i++) {
  SzeroText value=codec->members[i].identity[0];
  if(szero_lan_identity_valid(value.data,value.size)) {
   if(view.count==SZERO_MATERIALIZER_MAX_MEMBERS) return;
   memcpy(view.principal[view.count++],value.data,38);
  }
 }
 if(view.count<SZERO_MATERIALIZER_MAX_MEMBERS+1) memcpy(view.principal[view.count++],native_lan_primary,38);
 unsigned slot=4;
 for(unsigned i=0;i<4;i++) {
  if(r->views[i].service==service) {slot=i;break;}
  if(!r->views[i].service && slot==4) slot=i;
 }
 if(slot<4) r->views[slot]=view;
}
