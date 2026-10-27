/* Opt-in exact-build passive session evidence. Own-process RPM only: no
 * engine calls, hooks, game writes, sockets, identity strings or Lua API.
 * Call szero_session_probe from the same game thread, at most once per second.
 * Raw fields are evidence, NOT documented state enums or initialized sessions.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "native_image.h"
#include "native_bindings.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

static volatile LONG state; /* 0 new, 1 validating, 2 verified, 3 failed, 4 stopped */
static uintptr_t image_base;
static wchar_t output_path[32768];
static DWORD owner_thread;
static ULONGLONG started, last_poll;
static unsigned polls, records;
typedef struct {
    int available, session_present;
    int32_t field_63c;
    uint32_t mode_65c;
    unsigned char field_661,field_662,field_663,field_665,field_667,task_19d6;
    const char *reason;
} Sample;
static Sample previous;
static int have_previous;
#ifdef SZERO_SESSION_TEST
static unsigned read_count;
static uintptr_t mutate_global;
static unsigned mutate_at;
#endif

static int read_memory(uintptr_t address,void *out,SIZE_T bytes) {
    SIZE_T got=0;
#ifdef SZERO_SESSION_TEST
    read_count++;
    if (mutate_global && read_count==mutate_at) *(uintptr_t *)mutate_global=0;
#endif
    return address && ReadProcessMemory(GetCurrentProcess(),(const void *)address,out,bytes,&got) && got==bytes;
}

/* Only whitelisted scalar ranges are read. Pointers never leave this helper. */
static Sample take_sample(uintptr_t base) {
    Sample s={0}; uintptr_t context=0,after=0,vtable=0,after_vtable=0,session=0;
    s.reason="context_pointer_unreadable";
    if (!read_memory(base+szero_bind_rva(0x8cf84f8),&context,8)) return s;
    if (!context) { s.reason="context_absent"; return s; }
    s.reason="context_identity_unreadable";
    if (!read_memory(context,&vtable,8)) return s;
    if (vtable!=base+szero_bind_rva(0x7ba1bf8)) { s.reason="context_identity_mismatch"; return s; }
    s.reason="context_fields_unreadable";
#define READ_FIELD(offset, destination) if (!read_memory(context+(offset),&(destination),sizeof(destination))) return s
    READ_FIELD(0x40,session);
    READ_FIELD(0x63c,s.field_63c);
    READ_FIELD(0x65c,s.mode_65c);
    READ_FIELD(0x661,s.field_661);
    READ_FIELD(0x662,s.field_662);
    READ_FIELD(0x663,s.field_663);
    READ_FIELD(0x665,s.field_665);
    READ_FIELD(0x667,s.field_667);
    READ_FIELD(0x19d6,s.task_19d6);
#undef READ_FIELD
    s.reason="context_changed_during_read";
    if (!read_memory(base+szero_bind_rva(0x8cf84f8),&after,8) || after!=context ||
        !read_memory(context,&after_vtable,8) || after_vtable!=vtable) return s;
    s.available=1; s.session_present=session!=0; s.reason="snapshot";
    return s;
}

static int same_sample(const Sample *a,const Sample *b) {
    if (a->available!=b->available || strcmp(a->reason,b->reason)) return 0;
    if (!a->available) return 1;
    return a->session_present==b->session_present && a->field_63c==b->field_63c &&
        a->mode_65c==b->mode_65c && a->field_661==b->field_661 &&
        a->field_662==b->field_662 && a->field_663==b->field_663 &&
        a->field_665==b->field_665 && a->field_667==b->field_667 && a->task_19d6==b->task_19d6;
}

static int append_sample(const Sample *s) {
    SYSTEMTIME t; GetSystemTime(&t);
    if (records>=256) return 0;
    FILE *f=_wfopen(output_path,L"ab"); if (!f) return 0;
    fprintf(f,"{\"version\":1,\"utc\":\"%04u-%02u-%02uT%02u:%02u:%02u.%03uZ\","
        "\"tick_ms\":%llu,\"pid\":%lu,\"validation\":\"native_layout\",\"available\":%s,\"reason\":\"%s\"",
        t.wYear,t.wMonth,t.wDay,t.wHour,t.wMinute,t.wSecond,t.wMilliseconds,
        (unsigned long long)GetTickCount64(),GetCurrentProcessId(),
        s->available?"true":"false",s->reason);
    if (s->available) fprintf(f,",\"consistent_identity\":true,\"session_present\":%s,\"field_63c_raw\":%ld,"
        "\"mode_65c_raw\":%lu,\"field_661_raw\":%u,\"field_662_raw\":%u,\"field_663_raw\":%u,"
        "\"field_665_raw\":%u,\"field_667_raw\":%u,\"task_19d6_raw\":%u",
        s->session_present?"true":"false",(long)s->field_63c,(unsigned long)s->mode_65c,
        s->field_661,s->field_662,s->field_663,s->field_665,s->field_667,s->task_19d6);
    fputs(",\"limits\":\"Read-only non-atomic scalar snapshot; raw fields have unresolved semantics; session presence is not readiness.\"}\n",f);
    int ok=!ferror(f); if (fclose(f)) ok=0;
    if (ok) records++;
    return ok;
}

static void stop_reason(const char *reason) {
    Sample s={0};s.reason=reason; append_sample(&s); InterlockedExchange(&state,4);
}

static DWORD WINAPI verify_image(void *module) {
    int valid=szero_native_image(image_base,0) && szero_bindings_init(image_base);
    InterlockedExchange(&state,valid?2:3);
    if(module) FreeLibraryAndExitThread((HMODULE)module,0);
    return 0;
}

static int prepare(void) {
    HMODULE own; wchar_t instance[65],enabled[3],*slash;
    if (GetEnvironmentVariableW(L"SZERO_LAN_NATIVE_TRACE",enabled,3)!=1 || enabled[0]!=L'1') return 0;
    DWORD size=GetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",instance,65);
    if (!size || size>=65) return 0;
    for (DWORD i=0;i<size;i++) if (!((instance[i]>=L'a' && instance[i]<=L'f') || (instance[i]>=L'0' && instance[i]<=L'9'))) return 0;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
        (const wchar_t *)(uintptr_t)&prepare,&own) || !GetModuleFileNameW(own,output_path,32768)) return 0;
    slash=wcsrchr(output_path,L'\\'); if (!slash || slash-output_path>32500) return 0;
    swprintf(slash+1,200,L"session_trace_%ls.jsonl",instance);
    if (!DeleteFileW(output_path) && GetLastError()!=ERROR_FILE_NOT_FOUND) return 0;
    owner_thread=GetCurrentThreadId(); image_base=(uintptr_t)GetModuleHandleW(NULL);
    return image_base!=0;
}

__declspec(dllexport) int szero_session_probe(void *lua_state) {
    (void)lua_state;
    LONG current=InterlockedCompareExchange(&state,1,0);
    if (!current) {
        if (!prepare()) { InterlockedExchange(&state,4); return 0; }
        HMODULE keep_alive=NULL;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,(const wchar_t *)(uintptr_t)&prepare,&keep_alive)) { stop_reason("module_lifetime"); return 0; }
        HANDLE worker=CreateThread(NULL,0,verify_image,keep_alive,0,NULL);
        if (!worker) { FreeLibrary(keep_alive);stop_reason("validation_worker"); }
        else CloseHandle(worker);
        return 0;
    }
    if (current==1 || current==4) return 0;
    if (GetCurrentThreadId()!=owner_thread) return 0; /* no snapshot on another thread */
    if (current==3) { stop_reason("native_image_layout_unavailable"); return 0; }
    ULONGLONG now=GetTickCount64();
    if (!started) started=now;
    if (polls>=300 || now-started>=300000 || records>=255) { stop_reason("capture_limit_reached"); return 0; }
    if (last_poll && now-last_poll<1000) return 0;
    last_poll=now; polls++;
    Sample s=take_sample(image_base);
    if (!have_previous || !same_sample(&s,&previous)) {
        if (!append_sample(&s)) { InterlockedExchange(&state,4); return 0; }
        previous=s;have_previous=1;
    }
    return 0;
}

#ifdef SZERO_SESSION_TEST
#include <assert.h>
int main(void) {
    unsigned char *context=VirtualAlloc(NULL,0x3000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);assert(context);
    uintptr_t global=(uintptr_t)context,base=(uintptr_t)&global-0x8cf84f8,vt=base+szero_bind_rva(0x7ba1bf8);
    memcpy(context,&vt,8); uintptr_t session=123;memcpy(context+0x40,&session,8);
    int32_t field=-5;memcpy(context+0x63c,&field,4);context[0x65c]=3;context[0x667]=7;context[0x19d6]=9;
    read_count=0;Sample s=take_sample(base);assert(s.available && s.session_present && s.field_63c==-5 && s.mode_65c==3 && s.field_667==7 && s.task_19d6==9);assert(read_count==13);
    Sample before=s;assert(same_sample(&s,&before));s.mode_65c++;assert(!same_sample(&s,&before));
    s=take_sample((uintptr_t)1-0x8cf84f8);assert(!s.available && !strcmp(s.reason,"context_pointer_unreadable"));
    global=0;s=take_sample(base);assert(!s.available && !strcmp(s.reason,"context_absent"));
    global=(uintptr_t)context;context[0]^=1;s=take_sample(base);assert(!s.available && !strcmp(s.reason,"context_identity_mismatch"));context[0]^=1;
    global=1;s=take_sample(base);assert(!s.available && !strcmp(s.reason,"context_identity_unreadable"));
    global=(uintptr_t)context;DWORD old;assert(VirtualProtect(context+0x1000,0x1000,PAGE_NOACCESS,&old));
    s=take_sample(base);assert(!s.available && !strcmp(s.reason,"context_fields_unreadable"));assert(VirtualProtect(context+0x1000,0x1000,old,&old));
    read_count=0;mutate_global=(uintptr_t)&global;mutate_at=12;s=take_sample(base);assert(!s.available && !strcmp(s.reason,"context_changed_during_read"));mutate_global=0;
    wchar_t temp[MAX_PATH];assert(GetTempPathW(MAX_PATH,temp));swprintf(output_path,32768,L"%lsSzeroSessionTest-%lu.jsonl",temp,GetCurrentProcessId());
    DeleteFileW(output_path);before=take_sample(base);assert(append_sample(&before));
    FILE *f=_wfopen(output_path,L"rb");assert(f);char data[4096]={0};assert(fread(data,1,sizeof(data)-1,f));fclose(f);
    assert(strstr(data,"context_absent") && !strstr(data,"mode_65c_raw") && !strstr(data,"session_present"));
    global=(uintptr_t)context;image_base=base;owner_thread=GetCurrentThreadId();state=2;records=0;read_count=0;
    szero_session_probe(NULL);assert(read_count==13 && records==1);
    unsigned reads=read_count;szero_session_probe(NULL);assert(read_count==reads && records==1);
    owner_thread++;last_poll=0;szero_session_probe(NULL);assert(read_count==reads);owner_thread--;
    polls=300;szero_session_probe(NULL);assert(state==4 && read_count==reads && records==2);
    records=256;assert(!append_sample(&before));verify_image(NULL);assert(state==3);
    assert(DeleteFileW(output_path));assert(VirtualFree(context,0,MEM_RELEASE));
    puts("Native session scalar fixture tests passed (not a game integration test)");return 0;
}
#endif
