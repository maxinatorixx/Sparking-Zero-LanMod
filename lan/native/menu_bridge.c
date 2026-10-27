/* Experimental exact-build UI-only bridge. Unlike console_probe.c this calls
 * one native engine function, only to bind newly created LAN menu buttons.
 * No network, authentication, travel, executable patch or existing menu edits.
 * Invoke szero_menu_bridge only in ExecuteInGameThread. No Lua API linkage.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "native_image.h"
#include "native_bindings.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

static volatile LONG state; /* 0=new, 1=validating, 2=verified, 3=failed */
static uintptr_t image_base;
static DWORD owner_thread;
static unsigned long last_serial;
static wchar_t report_path[32768], request_path[32768];
#ifdef SZERO_MENU_TEST
static unsigned fixture_bind_count;
#endif
static int read_memory(uintptr_t at,void *out,SIZE_T length) {
    SIZE_T got=0;
    return at && ReadProcessMemory(GetCurrentProcess(),(void *)at,out,length,&got) && got==length;
}
static uint64_t u64(const unsigned char *p) { uint64_t n;memcpy(&n,p,8);return n; }
static uint32_t u32(const unsigned char *p) { uint32_t n;memcpy(&n,p,4);return n; }
static void report(const char *status,const char *reason,unsigned long serial) {
    FILE *f=_wfopen(report_path,L"wb");
    if(f) { fprintf(f,"{\"version\":1,\"status\":\"%s\",\"reason\":\"%s\",\"pid\":%lu,\"serial\":%lu}\n",
        status,reason,GetCurrentProcessId(),serial);fclose(f); }
}
static DWORD WINAPI verify(void *keep_alive) {
    int valid=szero_native_image(image_base,0) && szero_bindings_init(image_base);
    InterlockedExchange(&state,valid?2:3);
    if(keep_alive) FreeLibraryAndExitThread((HMODULE)keep_alive,0);
    return 0;
}
static int prepare(void) {
    HMODULE own; wchar_t instance[65],*slash;
    DWORD size=GetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",instance,65);
    if(size && size<65) { for(DWORD n=0;n<size;n++)
        if(!((instance[n]>=L'a'&&instance[n]<=L'f')||(instance[n]>=L'0'&&instance[n]<=L'9'))) return 0;
    } else if(size) return 0; else wcscpy(instance,L"default");
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        (const wchar_t *)(uintptr_t)&prepare,&own)) return 0;
    if(!GetModuleFileNameW(own,report_path,32768)) return 0;
    slash=wcsrchr(report_path,L'\\'); if(!slash || (size_t)(slash-report_path)>32500) return 0;
    swprintf(slash+1,200,L"menu_bridge_%ls.json",instance);
    wcscpy(request_path,report_path);
    slash=wcsrchr(request_path,L'.'); wcscpy(slash,L".request");
    DeleteFileW(request_path); DeleteFileW(report_path);
    image_base=(uintptr_t)GetModuleHandleW(NULL); owner_thread=GetCurrentThreadId();
    return image_base!=0;
}
static int object(uintptr_t at,uintptr_t vtable,unsigned char *out,SIZE_T size) {
    return !(at&7) && read_memory(at,out,size) && u64(out)==vtable &&
        !(u32(out+8)&0x60018030u) && u64(out+0x10)!=0;
}
/* Validate every object before ANY native invocation. Only fresh base-class
 * instances whose Outer chain is button -> LAN root tree -> LAN root qualify.
 */
static int validate(uintptr_t root,uintptr_t tree,const uintptr_t *buttons,unsigned count) {
    unsigned char r[0x228],t[0x28],b[0x28];
    uintptr_t root_class=0,button_class=0;
#ifdef SZERO_MENU_TEST
    root_class=1;button_class=2;
#else
    if(!read_memory(image_base+szero_bind_rva(0x86f7360),&root_class,8) || !root_class ||
       !read_memory(image_base+szero_bind_rva(0x86f6b68),&button_class,8) || !button_class) return 0;
#endif
    if(count<1 || count>8 || root==tree || (tree&7) ||
        !object(root,image_base+szero_bind_rva(0x6bc13e8),r,sizeof(r)) || u64(r+0x220)!=tree ||
        u64(r+0x10)!=root_class ||
        !read_memory(tree,t,sizeof(t)) || u64(t+0x20)!=root ||
        (u32(t+8)&0x60018030u) || !u64(t+0x10)) return 0;
    for(unsigned n=0;n<count;n++) {
        if(buttons[n]==root || buttons[n]==tree ||
            !object(buttons[n],image_base+szero_bind_rva(0x6bb0490),b,sizeof(b)) ||
            u64(b+0x10)!=button_class || u64(b+0x20)!=tree) return 0;
        for(unsigned j=0;j<n;j++) if(buttons[j]==buttons[n]) return 0;
    }
    return 1;
}
static void bind_buttons(uintptr_t root,const uintptr_t *buttons,unsigned count) {
#ifdef SZERO_MENU_TEST
    (void)root;(void)buttons;fixture_bind_count+=count;
#else
    void (*bind_one)(void *,void *)=(void (*)(void *,void *))(image_base+szero_bind_rva(0x2b380c0));
    for(unsigned n=0;n<count;n++) bind_one((void *)root,(void *)buttons[n]);
#endif
}
static void consume(void) {
    FILE *f=_wfopen(request_path,L"rb");
    unsigned long pid=0,serial=0; unsigned count=0;
    unsigned long long root=0,tree=0,raw[8]={0}; uintptr_t buttons[8]; char magic[20]={0};
    int valid=0;
    if(!f) { report("ready","native_image_validated",last_serial);return; }
    if(fseek(f,0,SEEK_END)) goto done;
    long size=ftell(f);
    if(size<1 || size>512 || fseek(f,0,SEEK_SET)) goto done;
    if(fscanf(f,"%19s %lu %lu %llx %llx %u",magic,&pid,&serial,&root,&tree,&count)!=6 ||
        strcmp(magic,"SZERO_MENU_V1") || pid!=GetCurrentProcessId() || !serial ||
        serial<=last_serial || count<1 || count>8) goto done;
    for(unsigned n=0;n<count;n++) { if(fscanf(f,"%llx",&raw[n])!=1) goto done;buttons[n]=(uintptr_t)raw[n]; }
    if(fscanf(f," %19s",magic)!=EOF) goto done;
    valid=1;
done:
    fclose(f); DeleteFileW(request_path);
    if(!valid) { report("rejected","request_bounds_identity_or_replay",serial);return; }
    last_serial=serial;
    if(!validate((uintptr_t)root,(uintptr_t)tree,buttons,count)) { report("rejected","owned_widget_identity",serial);return; }
    static const unsigned char code[]={0x48,0x85,0xd2,0x0f,0x84,0x10,0x01,0,0,0x56,0x48,0x83,0xec,0x40};
    if(!szero_bind_prefix(image_base,0x2b380c0,code,sizeof(code))) {
        report("rejected","native_binding_code_changed",serial);return;
    }
    bind_buttons((uintptr_t)root,buttons,count);
    report("bound","native_buttons_registered_not_runtime_ui_verified",serial);
}
__declspec(dllexport) int szero_menu_bridge(void *lua_state) {
    (void)lua_state;
    LONG current=InterlockedCompareExchange(&state,1,0);
    if(current==0) {
        if(!prepare()) { InterlockedExchange(&state,3);return 0; }
        report("validating","verification_in_background",0);
        HMODULE own=NULL;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
            (const wchar_t *)(uintptr_t)&prepare,&own)) { InterlockedExchange(&state,3);return 0; }
        HANDLE worker=CreateThread(NULL,0,verify,own,0,NULL);
        if(worker) CloseHandle(worker); else { FreeLibrary(own);InterlockedExchange(&state,3); }
    } else if(GetCurrentThreadId()!=owner_thread) report("rejected","wrong_calling_thread",0);
    else if(current==2) consume();
    else if(current==3) report("unavailable","native_image_layout_unavailable",0);
    return 0;
}
#ifdef SZERO_MENU_TEST
#include <assert.h>
int main(void) {
    unsigned char root[0x228]={0},tree[0x28]={0},button[0x28]={0};
    /* A module-backed fixture buffer keeps the synthetic canonical base from
     * wrapping below zero on Wine's low-address stack. */
    static unsigned char binding_code[]={0x48,0x85,0xd2,0x0f,0x84,0x10,0x01,0,0,0x56,0x48,0x83,0xec,0x40};
    uintptr_t child=(uintptr_t)button; uint64_t n;
    image_base=(uintptr_t)binding_code-0x2b380c0;
    n=image_base+szero_bind_rva(0x6bc13e8);memcpy(root,&n,8);n=1;memcpy(root+0x10,&n,8);
    n=(uintptr_t)tree;memcpy(root+0x220,&n,8);n=(uintptr_t)root;memcpy(tree+0x20,&n,8);
    n=1;memcpy(tree+0x10,&n,8);n=2;memcpy(button+0x10,&n,8);
    n=image_base+szero_bind_rva(0x6bb0490);memcpy(button,&n,8);n=(uintptr_t)tree;memcpy(button+0x20,&n,8);
    assert(validate((uintptr_t)root,(uintptr_t)tree,&child,1));
    button[8]=0x10;assert(!validate((uintptr_t)root,(uintptr_t)tree,&child,1));button[8]=0;
    n=0;memcpy(button+0x20,&n,8);assert(!validate((uintptr_t)root,(uintptr_t)tree,&child,1));
    assert(!validate(1,(uintptr_t)tree,&child,1));assert(!validate((uintptr_t)root,(uintptr_t)tree,&child,9));
    n=(uintptr_t)tree;memcpy(button+0x20,&n,8);
    uintptr_t duplicates[]={child,child};assert(!validate((uintptr_t)root,(uintptr_t)tree,duplicates,2));
    tree[8]=0x20;assert(!validate((uintptr_t)root,(uintptr_t)tree,&child,1));tree[8]=0;
    wchar_t temp[MAX_PATH];assert(GetTempPathW(MAX_PATH,temp));
    swprintf(report_path,32768,L"%lsSzeroMenuTest-%lu.json",temp,GetCurrentProcessId());
    swprintf(request_path,32768,L"%lsSzeroMenuTest-%lu.request",temp,GetCurrentProcessId());
    FILE *f=_wfopen(request_path,L"wb");assert(f);
    fprintf(f,"SZERO_MENU_V1 %lu 1 %llx %llx 1\n%llx\n",GetCurrentProcessId(),
        (unsigned long long)(uintptr_t)root,(unsigned long long)(uintptr_t)tree,(unsigned long long)child);fclose(f);
    consume();assert(fixture_bind_count==1);
    f=_wfopen(report_path,L"rb");assert(f);char result[512]={0};assert(fread(result,1,511,f)>0);fclose(f);
    assert(strstr(result,"\"status\":\"bound\""));
    f=_wfopen(request_path,L"wb");assert(f);fprintf(f,"SZERO_MENU_V1 %lu 1 0 0 1\n0\n",GetCurrentProcessId());fclose(f);
    consume();assert(fixture_bind_count==1);
    f=_wfopen(report_path,L"rb");assert(f);memset(result,0,sizeof(result));assert(fread(result,1,511,f)>0);fclose(f);
    assert(strstr(result,"request_bounds_identity_or_replay"));
    binding_code[0]=0;
    f=_wfopen(request_path,L"wb");assert(f);
    fprintf(f,"SZERO_MENU_V1 %lu 2 %llx %llx 1\n%llx\n",GetCurrentProcessId(),
        (unsigned long long)(uintptr_t)root,(unsigned long long)(uintptr_t)tree,(unsigned long long)child);fclose(f);
    consume();assert(fixture_bind_count==1);
    f=_wfopen(report_path,L"rb");assert(f);memset(result,0,sizeof(result));assert(fread(result,1,511,f)>0);fclose(f);
    assert(strstr(result,"native_binding_code_changed"));
    assert(DeleteFileW(report_path));
    puts("Native menu ownership, request/replay and code-guard fixtures passed; no game/native UI call made");return 0;
}
#endif
