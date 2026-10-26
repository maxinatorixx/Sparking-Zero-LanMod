#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "native_session_host.h"
#include <string.h>

static int read_mem(uintptr_t p, void *out, size_t size) {
    SIZE_T got=0;
    return p && ReadProcessMemory(GetCurrentProcess(),(const void *)p,out,size,&got) && got==size;
}
static int fail(SzeroNativeSessionHost *h, uint32_t reason) {
    if(h) h->last_error=reason;
    return 0;
}
static int executable_image(SzeroNativeSessionHost *h, uintptr_t address) {
    MEMORY_BASIC_INFORMATION info;
    if(VirtualQuery((const void *)address,&info,sizeof(info))!=sizeof(info) ||
       info.State!=MEM_COMMIT || (uintptr_t)info.AllocationBase!=h->image_base ||
       info.Type!=MEM_IMAGE || (info.Protect&(PAGE_GUARD|PAGE_NOACCESS))) return 0;
    DWORD p=info.Protect&0xff;
    return p==PAGE_EXECUTE || p==PAGE_EXECUTE_READ ||
        p==PAGE_EXECUTE_READWRITE || p==PAGE_EXECUTE_WRITECOPY;
}
int szero_native_session_host_ready(SzeroNativeSessionHost *h) {
    if(!h || h->exact_hash_verified!=1 || !h->image_base || !h->service ||
       !h->expected_vptr || !h->native_thread_id || !h->owns_vptr)
        return fail(h,SZERO_HOST_CONFIG);
    if(h->image_base!=(uintptr_t)GetModuleHandleW(NULL) ||
       h->image_base>UINTPTR_MAX-0x8cf84f8) return fail(h,SZERO_HOST_IMAGE);
    if(h->native_thread_id!=GetCurrentThreadId()) return fail(h,SZERO_HOST_THREAD);
    uintptr_t ctx=0, vt=0, bundle=0, service=0;
    unsigned char selector=0;
    if(!read_mem(h->image_base+0x8cf84f8,&ctx,8) ||
       !read_mem(ctx,&vt,8) || vt!=h->image_base+0x7ba1bf8 ||
       !read_mem(ctx+8,&bundle,8) || !read_mem(ctx+0x667,&selector,1) ||
       !read_mem(bundle+(selector?0x50:0x48),&service,8) || service!=h->service)
        return fail(h,SZERO_HOST_CONTEXT);
    if(!read_mem(service,&vt,8) || vt!=h->expected_vptr ||
       !h->owns_vptr(h->vptr_owner,service,vt)) return fail(h,SZERO_HOST_VPTR);
    /* Hash guards on-disk build; this additionally rejects non-image/unmapped
     * runtime destinations. No writable/executable mapping is created here. */
    static const uintptr_t functions[]={0x5943940,0x592d690,0x1dcc4a0,
        0x58cbbf0,0x5945540,0x58caf50,0x59263a0,0x59263b0};
    for(size_t i=0;i<sizeof(functions)/sizeof(functions[0]);i++)
        if(!executable_image(h,h->image_base+functions[i]))
            return fail(h,SZERO_HOST_FUNCTION);
    h->last_error=SZERO_HOST_OK;
    return 1;
}
static int callback_ready(void *context) {
    return szero_native_session_host_ready(context);
}
static int validate_pair(void *context, const uintptr_t pair[2]) {
    SzeroNativeSessionHost *h=context;
    uintptr_t vt=0, destroy=0, deallocate=0;
    LONG64 strong=0, weak=0;
    if(!pair[0] || pair[0]>UINTPTR_MAX-0xe8 || pair[1]!=pair[0]+0xe8 ||
       (pair[1]&7) || !read_mem(pair[1],&vt,8) || vt!=h->image_base+0x7b99d90 ||
       !read_mem(pair[1]+8,&strong,8) || !read_mem(pair[1]+16,&weak,8) ||
       strong<=0 || weak<=0 || !read_mem(vt+0x20,&destroy,8) ||
       !read_mem(vt+0x28,&deallocate,8) || destroy!=h->image_base+0x59263a0 ||
       deallocate!=h->image_base+0x59263b0) return fail(h,SZERO_HOST_PAIR);
    MEMORY_BASIC_INFORMATION info;
    if(VirtualQuery((const void *)pair[1],&info,sizeof(info))!=sizeof(info) ||
       info.State!=MEM_COMMIT || (info.Protect&(PAGE_GUARD|PAGE_NOACCESS)) ||
       info.RegionSize<24 || pair[1]<(uintptr_t)info.BaseAddress ||
       pair[1]-(uintptr_t)info.BaseAddress>info.RegionSize-24 ||
       !((info.Protect&0xff)==PAGE_READWRITE ||
         (info.Protect&0xff)==PAGE_EXECUTE_READWRITE ||
         (info.Protect&0xff)==PAGE_WRITECOPY ||
         (info.Protect&0xff)==PAGE_EXECUTE_WRITECOPY)) return fail(h,SZERO_HOST_PAIR);
    h->last_error=SZERO_HOST_OK;
    return 1;
}
static void localize(void *context, uintptr_t descriptor) {
    SzeroNativeSessionHost *h=context;
    typedef void (SZERO_NATIVE_CALL *Fn)(uintptr_t,uintptr_t);
    ((Fn)(h->image_base+0x592d690))(h->service,descriptor);
}
static void copy_string(void *context, SzeroNativeString *out, SzeroText text) {
    SzeroNativeSessionHost *h=context;
    typedef void *(SZERO_NATIVE_CALL *Fn)(void *,const void *,size_t,size_t);
    ((Fn)(h->image_base+0x1dcc4a0))(out,text.data,text.size,text.size);
}
static void destroy_string(void *context,SzeroNativeString *owned) {
    SzeroNativeSessionHost *h=context;
    /* Only a string allocated by our original native copy_string callback is
     * admitted. This is the same allocator-tag branch retained in original
     * create/leave/error cleanup, NOT CRT free and not a server-supplied ptr. */
    if(owned->words[0]&1) {
        uintptr_t allocator=(uintptr_t)(owned->words[0]&~UINT64_C(3));
        if(!allocator) allocator=*(uintptr_t *)(h->image_base+0x8cf7900);
        typedef void (SZERO_NATIVE_CALL *Fn)(uintptr_t,uintptr_t);
        uintptr_t vtable=*(uintptr_t *)allocator;
        ((Fn)(*(uintptr_t *)(vtable+0x28)))(allocator,(uintptr_t)owned->words[1]);
    }
    memset(owned,0,sizeof(*owned));
}
static void cache_consume(void *context, uintptr_t pair[2]) {
    SzeroNativeSessionHost *h=context;
    typedef void (SZERO_NATIVE_CALL *Fn)(uintptr_t,uintptr_t *);
    ((Fn)(h->image_base+0x58cbbf0))(h->service,pair);
    pair[0]=pair[1]=0;
}
static void release_pair(void *context, uintptr_t pair[2]) {
    SzeroNativeSessionHost *h=context;
    /* Pair was verified immediately after factory and its independent strong
     * reference remains owned throughout synchronous clone/release. */
    uintptr_t control=pair[1];
    typedef void (SZERO_NATIVE_CALL *Fn)(uintptr_t);
    pair[0]=pair[1]=0;
    if(InterlockedDecrement64((volatile LONG64 *)(control+8))==0) {
        ((Fn)(h->image_base+0x59263a0))(control);
        if(InterlockedDecrement64((volatile LONG64 *)(control+16))==0)
            ((Fn)(h->image_base+0x59263b0))(control);
    }
}
static void clone_descriptor(void *context,SzeroNativeDescriptor *out,uintptr_t source) {
    SzeroNativeSessionHost *h=context;
    typedef void *(SZERO_NATIVE_CALL *Fn)(void *,uintptr_t);
    ((Fn)(h->image_base+0x5945540))(out,source);
}
static void diff_consume(void *context,SzeroNativeDescriptor *owned,uint8_t settings) {
    SzeroNativeSessionHost *h=context;
    typedef void (SZERO_NATIVE_CALL *Fn)(uintptr_t,void *,unsigned char);
    ((Fn)(h->image_base+0x58caf50))(h->service,owned,settings);
}
int szero_native_session_host_bind(SzeroNativeSessionHost *h,
    const SzeroStreamWire *stream,SzeroNativeSessionCallbacks *out) {
    if(!h || !out || h->image_base>UINTPTR_MAX-0x8cf84f8) return fail(h,SZERO_HOST_CONFIG);
    SzeroNativeSessionCallbacks cb={0};
    cb.context=h; cb.ready=callback_ready;
    cb.factory=(SzeroDescriptorFactory)(h->image_base+0x5943940);
    cb.stream=stream; cb.image_base=h->image_base;
    cb.validate_pair=validate_pair; cb.localize=localize; cb.copy_string=copy_string;
    cb.cache_consume=cache_consume; cb.release_pair=release_pair;
    cb.clone_descriptor=clone_descriptor; cb.diff_consume=diff_consume;
    cb.destroy_string=destroy_string;
    *out=cb;
    return 1;
}
