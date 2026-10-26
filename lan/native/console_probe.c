/* Exact-build, read-only console registration audit. No engine function calls,
 * hooks, writes to game memory, sockets, platform calls or Lua API dependency.
 * szero_console_probe is a Lua C function: ignores lua_State*, returns 0 values.
 * Call from ExecuteInGameThread; hashing runs separately before memory reads.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

static const char expected_hash[] = "e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55";
static const wchar_t *names[] = {
    L"spn.multiplayerContext.contextMode",
    L"spn.multiplayerContext.contextMode.value",
    L"spn.multiplayerContext.myDummyMatchingJoinOrder",
    L"spn.multiplayerContext.myDummyMatchingJoinOrder.value",
    L"spn.multiplayerContext.myDummyP2pAddress",
    L"spn.multiplayerContext.myDummyP2pAddress.value",
    L"spn.multiplayerContext.dummyPeerP2pAddresses",
    L"spn.multiplayerContext.dummyPeerP2pAddresses.value",
    L"spn.multiplayerContext.apply",
    L"spn.multiplayerContext.apply.exec",
};
static volatile LONG state; /* 0=new, 1=hashing, 2=verified, 3=failed, 4=reported */
static wchar_t output_path[32768];
static uintptr_t image_base;

static int read_memory(uintptr_t address, void *destination, SIZE_T length) {
    SIZE_T actual = 0;
    return address && ReadProcessMemory(GetCurrentProcess(), (const void *)address,
        destination, length, &actual) && actual == length;
}
static uint64_t u64(const unsigned char *p) { uint64_t n; memcpy(&n,p,8); return n; }
static int32_t i32(const unsigned char *p) { int32_t n; memcpy(&n,p,4); return n; }

static void failure(const char *reason) {
    FILE *f = _wfopen(output_path, L"wb");
    if (f) {
        fprintf(f, "{\"version\":1,\"status\":\"unavailable\",\"reason\":\"%s\",\"pid\":%lu}\n", reason, GetCurrentProcessId());
        fclose(f);
    }
}

static DWORD WINAPI verify_image(void *unused) {
    wchar_t exe[32768];
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    unsigned char digest[32], buffer[65536];
    char hex[65];
    HANDLE file = INVALID_HANDLE_VALUE;
    DWORD count;
    int valid = 0;
    if (!GetModuleFileNameW(NULL, exe, 32768)) goto done;
    file = CreateFileW(exe, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        NULL, OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
    if (file == INVALID_HANDLE_VALUE) goto done;
    if (BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, NULL, 0) < 0) goto done;
    if (BCryptCreateHash(alg, &hash, NULL, 0, NULL, 0, 0) < 0) goto done;
    for (;;) {
        if (!ReadFile(file, buffer, sizeof(buffer), &count, NULL)) goto done;
        if (!count) break;
        if (BCryptHashData(hash, buffer, count, 0) < 0) goto done;
    }
    if (BCryptFinishHash(hash, digest, sizeof(digest), 0) < 0) goto done;
    for (unsigned n=0;n<32;n++) sprintf(hex+n*2,"%02x",digest[n]);
    valid = !strcmp(hex, expected_hash);
done:
    if (hash) BCryptDestroyHash(hash);
    if (alg) BCryptCloseAlgorithmProvider(alg, 0);
    if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
    InterlockedExchange(&state, valid ? 2 : 3);
    if (unused) FreeLibraryAndExitThread((HMODULE)unused,0);
    return 0;
}

static int prepare(void) {
    HMODULE own;
    wchar_t instance[65], *slash;
    DWORD size = GetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",instance,65);
    if (size && size < 65) {
        for (DWORD n=0;n<size;n++)
            if (!((instance[n]>=L'a' && instance[n]<=L'f') ||
                  (instance[n]>=L'0' && instance[n]<=L'9'))) return 0;
    } else if (size) return 0;
    else wcscpy(instance,L"default");
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
            GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            (const wchar_t *)(uintptr_t)&prepare, &own)) return 0;
    if (!GetModuleFileNameW(own,output_path,32768)) return 0;
    slash = wcsrchr(output_path,L'\\');
    if (!slash || (size_t)(slash-output_path)>32500) return 0;
    swprintf(slash+1, 200, L"console_probe_%ls.json", instance);
    /* Own generated report only; never consume a stale previous launch. */
    if (!DeleteFileW(output_path) && GetLastError()!=ERROR_FILE_NOT_FOUND) return 0;
    image_base=(uintptr_t)GetModuleHandleW(NULL);
    return image_base != 0;
}

static void snapshot(void) {
    unsigned char header[0x58], after[0x58];
    uintptr_t manager = 0;
    int present[sizeof(names)/sizeof(names[0])] = {0};
    int slots, capacity, bit_count, bit_capacity, free_count;
    unsigned occupied=0, read_names=0, invalid=0, spn_count=0;
    int control=0;
    unsigned char *entries=NULL, *flags=NULL;
    if (!read_memory(image_base+0x8739b48,&manager,sizeof(manager)) ||
        !read_memory(manager,header,sizeof(header)) ||
        u64(header) != image_base+0x6dc03c0) { failure("console_manager_identity"); return; }
    slots=i32(header+0x10); capacity=i32(header+0x14);
    bit_count=i32(header+0x30); bit_capacity=i32(header+0x34); free_count=i32(header+0x3c);
    if (slots<0 || slots>capacity || capacity>65536 || bit_count!=slots ||
        bit_capacity<slots || bit_capacity>1048576 || free_count<0 || free_count>slots) {
        failure("console_registry_bounds"); return;
    }
    SIZE_T flag_bytes=((SIZE_T)slots+31)/32*4;
    entries=HeapAlloc(GetProcessHeap(),0,(SIZE_T)slots*32+1);
    flags=HeapAlloc(GetProcessHeap(),0,flag_bytes+1);
    if (!entries || !flags) { failure("allocation"); goto done; }
    if (!read_memory(u64(header+8),entries,(SIZE_T)slots*32)) { failure("entry_read"); goto done; }
    if (u64(header+0x28)) {
        if (!read_memory(u64(header+0x28),flags,flag_bytes)) { failure("flag_read"); goto done; }
    } else {
        if (flag_bytes>16) { failure("inline_flags_bounds"); goto done; }
        memcpy(flags,header+0x18,flag_bytes);
    }
    for (int n=0;n<slots;n++) {
        if (!(flags[n/8] & (1u << (n%8)))) continue;
        occupied++;
        const unsigned char *entry=entries+(SIZE_T)n*32;
        int length=i32(entry+8), name_capacity=i32(entry+12);
        wchar_t name[512];
        if (length<2 || length>512 || name_capacity<length || name_capacity>4096 ||
            !read_memory(u64(entry),name,(SIZE_T)length*2) || name[length-1]) { invalid++; continue; }
        int valid_name=1;
        for (int k=0;k<length-1;k++) {
            unsigned c=(unsigned)name[k];
            if (c<32 || (c>=0xdc00 && c<=0xdfff)) { valid_name=0; break; }
            if (c>=0xd800 && c<=0xdbff) {
                if (k+1>=length-1 || name[k+1]<0xdc00 || name[k+1]>0xdfff) { valid_name=0; break; }
                k++;
            }
        }
        if (!valid_name) { invalid++; continue; }
        read_names++;
        if (!_wcsicmp(name,L"r.DumpingMovie")) control=1;
        if (!_wcsnicmp(name,L"spn.",4)) spn_count++;
        for (unsigned j=0;j<sizeof(names)/sizeof(names[0]);j++)
            if (!_wcsicmp(name,names[j])) present[j]=1;
    }
    if (!read_memory(manager,after,sizeof(after)) || memcmp(header,after,sizeof(header))) {
        failure("registry_changed_during_read"); goto done;
    }
    FILE *f=_wfopen(output_path,L"wb");
    if (!f) goto done;
    fprintf(f,"{\"version\":1,\"status\":\"snapshot\",\"target_sha256\":\"%s\",\"pid\":%lu,"
        "\"slots\":%d,\"occupied\":%u,\"names_read\":%u,\"invalid_names\":%u,\"spn_count\":%u,"
        "\"control_present\":%s,\"consistent_header\":true,\"complete_occupied_read\":%s,\"registered\":{",
        expected_hash,GetCurrentProcessId(),slots,occupied,read_names,invalid,spn_count,
        control?"true":"false", occupied==(unsigned)(slots-free_count) && read_names==occupied && control?"true":"false");
    for (unsigned j=0;j<sizeof(names)/sizeof(names[0]);j++)
        fprintf(f,"%s\"%ls\":%s",j?",":"",names[j],present[j]?"true":"false");
    fprintf(f,"},\"limits\":\"Registration snapshot only; retained/unregistered objects may exist; no command acceptance or session success proven.\"}\n");
    fclose(f);
done:
    if(entries) HeapFree(GetProcessHeap(),0,entries);
    if(flags) HeapFree(GetProcessHeap(),0,flags);
}

__declspec(dllexport) int szero_console_probe(void *lua_state) {
    (void)lua_state;
    LONG current=InterlockedCompareExchange(&state,1,0);
    if (current==0) {
        if (!prepare()) { InterlockedExchange(&state,4); return 0; }
        HMODULE keep_alive=NULL;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,
                (const wchar_t *)(uintptr_t)&prepare,&keep_alive)) {
            failure("module_lifetime"); InterlockedExchange(&state,4); return 0;
        }
        HANDLE worker=CreateThread(NULL,0,verify_image,keep_alive,0,NULL);
        if (!worker) { FreeLibrary(keep_alive); failure("hash_worker"); InterlockedExchange(&state,4); }
        else CloseHandle(worker);
    } else if (current==2 && InterlockedCompareExchange(&state,4,2)==2) snapshot();
    else if (current==3 && InterlockedCompareExchange(&state,4,3)==3) failure("target_hash_mismatch_or_unreadable");
    return 0;
}

#ifdef SZERO_PROBE_TEST
/* Native Windows fixture test, compiled as a separate EXE, never shipped as
 * the mod DLL. Exercises the same snapshot implementation with owned memory. */
#include <assert.h>
int main(void) {
    unsigned char header[0x58]={0}, entries[3*32]={0};
    uintptr_t manager=(uintptr_t)header;
    image_base=(uintptr_t)&manager-0x8739b48;
    uint64_t vtable=image_base+0x6dc03c0, data=(uintptr_t)entries;
    int32_t count=3;
    wchar_t temp[MAX_PATH];
    assert(GetTempPathW(MAX_PATH,temp));
    swprintf(output_path,32768,L"%lsSzeroProbeTest-%lu.json",temp,GetCurrentProcessId());
    memcpy(header,&vtable,8); memcpy(header+8,&data,8);
    memcpy(header+0x10,&count,4); memcpy(header+0x14,&count,4);
    memcpy(header+0x30,&count,4); memcpy(header+0x34,&count,4);
    header[0x18]=7;
    const wchar_t *fixture[]={L"r.DumpingMovie",L"SPN.MULTIPLAYERCONTEXT.CONTEXTMODE",names[8]};
    for (int i=0;i<3;i++) {
        uint64_t ptr=(uintptr_t)fixture[i];
        int32_t len=(int32_t)wcslen(fixture[i])+1;
        memcpy(entries+i*32,&ptr,8);
        memcpy(entries+i*32+8,&len,4); memcpy(entries+i*32+12,&len,4);
    }
    snapshot();
    FILE *f=_wfopen(output_path,L"rb"); assert(f);
    char result[8192]={0}; assert(fread(result,1,sizeof(result)-1,f)>0); fclose(f);
    assert(strstr(result,"\"complete_occupied_read\":true"));
    assert(strstr(result,"\"spn_count\":2"));
    assert(strstr(result,"\"spn.multiplayerContext.contextMode\":true"));
    assert(strstr(result,"\"spn.multiplayerContext.apply\":true"));
    assert(strstr(result,"\"spn.multiplayerContext.apply.exec\":false"));
    count=65537; memcpy(header+0x14,&count,4); snapshot();
    f=_wfopen(output_path,L"rb"); assert(f); memset(result,0,sizeof(result));
    assert(fread(result,1,sizeof(result)-1,f)>0); fclose(f);
    assert(strstr(result,"console_registry_bounds"));
    assert(!read_memory(1,result,8));
    verify_image(NULL);
    assert(state==3 && "fixture EXE must not pass the game identity guard");
    szero_console_probe(NULL);
    f=_wfopen(output_path,L"rb"); assert(f); memset(result,0,sizeof(result));
    assert(fread(result,1,sizeof(result)-1,f)>0); fclose(f);
    assert(strstr(result,"target_hash_mismatch_or_unreadable"));
    assert(DeleteFileW(output_path));
    puts("Native console registry fixture and bounds tests passed (not a game test)");
    return 0;
}
#endif
