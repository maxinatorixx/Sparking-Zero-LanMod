#define SZERO_BACKEND_ADAPTER_TEST
#include "backend_adapter.c"
#include <assert.h>

static unsigned projected,released,header_released,delegated,yields,nested;
static int cancel_next,bridge_mode;
static unsigned char request[80],out[104];
static const uintptr_t service_value=0x12340000;
static unsigned char rank_backend[256],rank_records[2][64];
__attribute__((noinline)) static void *fixture_exchange(uintptr_t service,uintptr_t output,uintptr_t input) {
    __asm__ __volatile__("nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop");
    (void)service;(void)input;++delegated;
    memset((void *)output,0x77,72);return (void *)0x9876;
}
static void *(*volatile call_entry)(uintptr_t,uintptr_t,uintptr_t)=fixture_exchange;
static unsigned maintenance_forwarded;
__attribute__((noinline)) static void *fixture_maintenance(uintptr_t a,uintptr_t output,uintptr_t c,
    uintptr_t d,uintptr_t e,uintptr_t category,uintptr_t g,uintptr_t h,uintptr_t i) {
    __asm__ __volatile__("nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop");
    assert(a==11 && c==33 && d==44 && e==55 && g==77 && h==88 && i==99);
    assert(category==2 || category==3);++maintenance_forwarded;
    memset((void *)output,0,40);SetLastError(9876);return (void *)123;
}
static void *(*volatile call_maintenance)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,
    uintptr_t,uintptr_t,uintptr_t,uintptr_t)=fixture_maintenance;
static unsigned result_forwarded;
__attribute__((noinline)) static void *fixture_battle_result(uintptr_t object,uintptr_t borrowed) {
    __asm__ __volatile__("nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop;nop");
    assert(object==0x4321);(void)borrowed;++result_forwarded;SetLastError(2222);return (void *)0xdeadbeef;
}
static void *(*volatile call_result)(uintptr_t,uintptr_t)=fixture_battle_result;
static DWORD WINAPI foreign_result(void *unused) {
    (void)unused;unsigned char value=1;SetLastError(1234);
    assert(call_result(0x4321,(uintptr_t)&value)==(void *)0xdeadbeef && GetLastError()==2222);return 0;
}
static void result_contract(void) {
    unsigned char value=1;SetLastError(1234);
    assert(call_result(0x4321,(uintptr_t)&value)==(void *)0xdeadbeef && GetLastError()==2222 && !result_value);
    const unsigned char *first=(const unsigned char *)"{\"res\":0,\"match_code\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\",\"match_phase\":0}";
    accept_battle_start(first,strlen((const char *)first));assert(!result_value);
    assert(call_result(0x4321,(uintptr_t)&value)==(void *)0xdeadbeef && result_value==1);
    accept_battle_start(first,strlen((const char *)first));assert(result_value==1);
    const unsigned char *second=(const unsigned char *)"{\"res\":0,\"match_code\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\",\"match_phase\":0}";
    accept_battle_start(second,strlen((const char *)second));assert(!result_value);
    HANDLE thread=CreateThread(NULL,0,foreign_result,NULL,0,NULL);assert(thread);
    assert(WaitForSingleObject(thread,1000)==WAIT_OBJECT_0);CloseHandle(thread);assert(!result_value);
    for(value=1;value<=3;value++) {
        assert(call_result(0x4321,(uintptr_t)&value)==(void *)0xdeadbeef && result_value==value);
    }
    value=2;call_result(0x4321,(uintptr_t)&value);result_sealed=1;
    value=1;call_result(0x4321,(uintptr_t)&value);assert(result_value==2);
    accept_battle_start(first,strlen((const char *)first));assert(!result_value && !result_sealed);
    value=7;call_result(0x4321,(uintptr_t)&value);assert(!result_value);
    value=2;call_result(0x4321,(uintptr_t)&value);assert(result_value==2);
    call_result(0x4321,1);assert(!result_value);
    memset(result_match_code,0,sizeof(result_match_code));
}
static void set_request(const char *url) {
    memset(request,0,sizeof(request));request[0]=1;
    uintptr_t data=(uintptr_t)url;uint64_t size=strlen(url);
    memcpy(request+8,&data,8);memcpy(request+16,&size,8);
    memcpy(request+24,&size,8);
}
static void guarded(void) {memset(out,0xa5,sizeof(out));}
static void check_guard(void) {
    for(unsigned i=0;i<16;++i) assert(out[i]==0xa5 && out[88+i]==0xa5);
}
static uint32_t output_code(void) {uint32_t n;memcpy(&n,out+24,4);return n;}
static void *fixture_current(void) {return (void *)0x1000;}
static unsigned char fixture_yield(void *task) {
    assert(task==(void *)0x1000);++yields;
    if(fixture_done_reached && job.state==QUEUED)
        InterlockedExchange(&fixture_pause_after_done,0);
    if(!nested) {
        unsigned char other[72];nested=1;memset(other,0xcc,sizeof(other));
        assert(call_entry(service_value,(uintptr_t)other,(uintptr_t)request)==other);
        assert(other[0]==1);
    }
    Sleep(1);
    return (unsigned char)(cancel_next && yields>4);
}
static void *fixture_factory(uintptr_t unused,SzeroBackendView **value) {
    assert(!unused);*value=HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,40);
    if(*value)(*value)->vtable=0x146d36f80;
    return value;
}
static void fixture_project(void *output,SzeroBackendRaw *raw) {
    ++projected;assert(GetCurrentThreadId()==game_thread);
    SzeroBackendView *view=(void *)raw->stream.object;
    assert(raw->status==200 && view->size>0 && view->size<=65536);
    assert(raw->headers.buckets==(uintptr_t)&raw->headers.inline_bucket);
    unsigned char *result=output;memset(result,0,72);
    int bridge_payload=0;
    if(bridge_mode) {
        char *copy=malloc((size_t)view->size+1);assert(copy);
        memcpy(copy,(void *)view->data,(size_t)view->size);copy[view->size]=0;
        bridge_payload=strstr(copy,"\"res\":0") != NULL;
        if(bridge_mode==1) bridge_payload=bridge_payload && strstr(copy,"\"session_code\"") &&
            strstr(copy,"szlan-") && strstr(copy,"\"rank_match_info_list\"") &&
            strstr(copy,"\"redirect_url\"");
        if(bridge_mode==3) {
            char *code=strstr(copy,"\"match_code\":\"");
            assert(code && strstr(copy,"\"match_phase\":0"));code+=14;
            for(unsigned i=0;i<32;i++)assert((code[i]>='0'&&code[i]<='9')||(code[i]>='a'&&code[i]<='f'));
            assert(code[32]=='"');
        }
        if(bridge_mode==4)assert(strstr(copy,"\"battle_result\"") && strstr(copy,"\"rank_match_info\"") && strstr(copy,"\"rank_point\":1234"));
        free(copy);assert(bridge_payload);
    }
    if(bridge_payload || (view->size==2 && !memcmp((void *)view->data,"{}",2)))result[0]=2;
    else {uint32_t code=0x57c77900;result[0]=1;memcpy(result+8,&code,4);}
}
static void fixture_stream(SzeroBackendOwner *owner) {
    ++released;assert(GetCurrentThreadId()==game_thread);
    assert(!owner->allocator && owner->object);
    HeapFree(GetProcessHeap(),0,(void *)owner->object);owner->object=0;
}
static void fixture_headers(SzeroBackendHeaders *headers) {
    ++header_released;assert(headers->buckets==(uintptr_t)&headers->inline_bucket);
}
static DWORD WINAPI other_thread(void *unused) {
    (void)unused;unsigned char output[72];
    assert(call_entry(service_value,(uintptr_t)output,(uintptr_t)request)==output);
    assert(output[0]==1);return 0;
}
static void wait_idle(void) {
    ULONGLONG end=GetTickCount64()+2000;
    while(job.state!=IDLE && GetTickCount64()<end)Sleep(5);
    assert(job.state==IDLE);
}
int wmain(int argc,wchar_t **argv) {
    assert(argc>=3);
    assert(native_rank_category==NULL);
    /* Native inline capacity depends on allocator-presence flag2: no allocator
     * permits30B, explicit allocator reserveslastword and permits22B. */
    {
        char path[96];
        memset(request,'x',sizeof(request));request[0]=30u<<2;
        assert(request_route((uintptr_t)request,path)==-1); /* Valid30, outsideourhost. */
        memset(request,'x',sizeof(request));request[0]=(23u<<2)|2u;
        assert(request_route((uintptr_t)request,path)==-2); /* AllocatorSSOoverflow. */
        memset(request,'x',sizeof(request));request[0]=(22u<<2)|2u;
        assert(request_route((uintptr_t)request,path)==-1);
        memset(request,'x',sizeof(request));request[0]=31u<<2;
        assert(request_route((uintptr_t)request,path)==-2);
        set_request("https://steam-lb.dbs.channel.or.jp/pvp/start_battle_player1.php");
        assert(request_route((uintptr_t)request,path)==6 && !strcmp(path,routes[6]));
        set_request("https://szero.invalid/pvp/start_battle_player2.php");
        assert(request_route((uintptr_t)request,path)==7 && !strcmp(path,routes[7]));
        set_request("https://szero.invalid/pvp/start_battle_player1.php?account=foreign");
        assert(request_route((uintptr_t)request,path)==-2);
    }
    {
        char target[65];const char *good="{\"session_code\":\"never-forward\",\"platform_user_id\":\"szlan:0123456789abcdef0123456789abcdef\",\"ignore\":[1,true,{}]}";
        assert(card_target((const unsigned char *)good,strlen(good),target));
        assert(!strcmp(target,"szlan:0123456789abcdef0123456789abcdef"));
        const char *bad[]={"{}","{\"platform_user_id\":7}","{\"platform_user_id\":\"a\",\"platform_user_id\":\"b\"}",
            "{\"platform_user_id\":\"a\",}","{\"platform_user_id\":\"a\"}x", "{\"platform_user_id\":\"a\",\"x\":01}"};
        for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++)assert(!card_target((const unsigned char *)bad[i],strlen(bad[i]),target));
        /* Synthetic native local identity chain; exact equality only. */
        uintptr_t context[3]={0},bundle[4]={0},slot=(uintptr_t)context;
        unsigned char user[0x240]={0};uintptr_t old_base=image_base;
        image_base=(uintptr_t)&slot-0x8cf84f8;context[0]=image_base+0x7ba1bf8;
        context[1]=(uintptr_t)bundle;bundle[3]=(uintptr_t)user;
        user[0x200]=17u<<2;memcpy(user+0x201,"76561198000000000",17);
        const char *body="{\"platform_user_id\":\"76561198000000000\"}";
        uint64_t n=strlen(body);request[40]=1;memcpy(request+48,&body,8);memcpy(request+56,&n,8);memcpy(request+64,&n,8);
        assert(normalize_card_target((uintptr_t)request,target) && !strcmp(target,"self"));
        user[0x201]='8';assert(!normalize_card_target((uintptr_t)request,target));
        for(unsigned i=0;i<sizeof(job.request_scratch);i++)assert(!job.request_scratch[i]);
        image_base=old_base;
    }
    {
        const char *json="{\"auth_info\":{\"ticket\":\"DO-NOT-FORWARD\"},\"match_code\":\"0123456789abcdef0123456789abcdef\",\"outcome\":1}";
        char code[33],snapshot[1024];int outcome=-1;
        assert(battle_values((const unsigned char *)json,strlen(json),1,code,&outcome) && outcome==1);
        const char *bad[]={"{}","{\"match_code\":\"a\",\"outcome\":1}",
            "{\"match_code\":\"0123456789abcdef0123456789abcdef\",\"outcome\":true}",
            "{\"match_code\":\"0123456789abcdef0123456789abcdef\",\"outcome\":1,\"outcome\":2}",
            "{\"match_code\":\"0123456789abcdef0123456789abcdef\",\"outcome\":1.0}"};
        for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++)assert(!battle_values((const unsigned char *)bad[i],strlen(bad[i]),1,code,&outcome));
        uintptr_t pointer=(uintptr_t)rank_records;uint64_t count=1;
        memcpy(rank_backend+0xf0,&pointer,8);memcpy(rank_backend+0xf8,&count,8);
        rank_records[0][0]=3u<<2;memcpy(rank_records[0]+1,"LAN",3);
        int32_t point=1234,previous=1000,next=2000;uint32_t streak=4,bits=0x3f000000;
        memcpy(rank_records[0]+0x20,&point,4);memcpy(rank_records[0]+0x24,&previous,4);memcpy(rank_records[0]+0x28,&next,4);
        memcpy(rank_records[0]+0x2c,&streak,4);memcpy(rank_records[0]+0x30,&bits,4);
        rank_records[0][0x35]=1;rank_records[0][0x37]=255;rank_records[0][0x38]=3;
        fixture_rank_backend=(uintptr_t)rank_backend;
        assert(rank_snapshot_cache(fixture_rank_backend,1,0,snapshot) && strstr(snapshot,"\"rank_point\":1234"));
        assert(rank_snapshot_cache(fixture_rank_backend,2,0,snapshot)==2);
        memcpy(rank_records[1],rank_records[0],64);count=2;memcpy(rank_backend+0xf8,&count,8);
        assert(!rank_snapshot_cache(fixture_rank_backend,1,0,snapshot));
        rank_records[1][0x36]=1;
        assert(rank_snapshot_cache(fixture_rank_backend,1,0,snapshot)==1);
        assert(rank_snapshot_cache(fixture_rank_backend,1,1,snapshot)==1);
        rank_records[1][0x36]=0;
        count=0;memcpy(rank_backend+0xf8,&count,8);
        assert(rank_snapshot_cache(fixture_rank_backend,1,0,snapshot)==2 && strstr(snapshot,"\"rank_point\":0"));
        count=33;memcpy(rank_backend+0xf8,&count,8);assert(!rank_snapshot_cache(fixture_rank_backend,1,0,snapshot));
        count=1;memcpy(rank_backend+0xf8,&count,8);
        bits=0x7f800000;memcpy(rank_records[0]+0x30,&bits,4);assert(!rank_snapshot_cache(fixture_rank_backend,1,0,snapshot));
        bits=0x3f000000;memcpy(rank_records[0]+0x30,&bits,4);
    }
    SetEnvironmentVariableW(L"SZERO_LAN_NATIVE_SESSION3",L"1");
    SetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",argv[1]);
    if(!wcscmp(argv[2],L"production")) {
        assert(argc==4);HMODULE dll=LoadLibraryW(argv[3]);assert(dll);
        int (*start)(void *);FARPROC symbol=GetProcAddress(dll,"szero_backend_adapter");
        memcpy(&start,&symbol,sizeof(start));assert(start);
        assert(!start(NULL));Sleep(800);
        puts("Incompatible production layout refused");return 0;
    }
    unsigned char before[32],before_gate[32],before_result[32];
    memcpy(before_result,(void *)&fixture_battle_result,32);memcpy(before,(void *)&fixture_exchange,32);
    memcpy(before_gate,(void *)&fixture_maintenance,32);
    fixture_entry=(uintptr_t)&fixture_exchange;
    maintenance_entry=(uintptr_t)&fixture_maintenance;
    battle_result_entry=(uintptr_t)&fixture_battle_result;
    SetEnvironmentVariableW(L"SZERO_LAN_ACCOUNT_MODE",L"1");
    int authenticated=!wcscmp(argv[2],L"authenticated");
    int quiet_profile=!wcscmp(argv[2],L"profilequiet");
    int profile_mode=!wcscmp(argv[2],L"profile") || quiet_profile;
    if(quiet_profile)SetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",L"0");
    int end_mode=!wcscmp(argv[2],L"end1")?1:!wcscmp(argv[2],L"end2")?2:0;
    int battle_mode=!wcscmp(argv[2],L"battle1")?1:!wcscmp(argv[2],L"battle2")?2:0;
    if(authenticated || battle_mode || end_mode || profile_mode) {
        wchar_t policy_path[32768];assert(GetModuleFileNameW(NULL,policy_path,32768));
        wchar_t *slash=wcsrchr(policy_path,L'\\');assert(slash);
        swprintf(slash+1,200,L"lan_runtime_%ls.account.policy",argv[1]);
        FILE *file=_wfopen(policy_path,L"wb");assert(file);assert(fwrite("1\n",1,2,file)==2);fclose(file);
    }
    current_task=fixture_current;yield_cancel=fixture_yield;
    native_factory=fixture_factory;native_project=fixture_project;
    native_release_stream=fixture_stream;native_release_headers=fixture_headers;
    assert(!szero_backend_adapter(NULL));
    ULONGLONG deadline=GetTickCount64()+3000;
    while(state==VERIFYING && GetTickCount64()<deadline)Sleep(5);
    assert(state==ARMED);result_contract();
    if(authenticated) {
        /* No Ranked detour for authenticated startup: optional service tracer
         * can still verify and install its original maintenance entry hook. */
        assert(!memcmp(before_gate,(void *)&fixture_maintenance,32));
        unsigned char plain[40];assert(call_maintenance(11,(uintptr_t)plain,33,44,55,2,77,88,99)==(void *)123);
        assert(maintenance_forwarded==1);
        /* ARMED precedes the worker's first endpoint poll. Ensure this fixture
         * actually published a lifetime before simulating its later removal. */
        deadline=GetTickCount64()+2000;
        while(!fixture_endpoint_seen){assert(GetTickCount64()<deadline);Sleep(5);}
        assert(DeleteFileW(account_policy));assert(DeleteFileW(endpoint));
        deadline=GetTickCount64()+2000;
        while(state==ARMED || state==STOPPING){assert(GetTickCount64()<deadline);Sleep(5);}
        assert(state==STOPPED && !memcmp(before,(void *)&fixture_exchange,32));
            assert(!memcmp(before_result,(void *)&fixture_battle_result,32));
        puts("Authenticated Ranked entry remains unpatched for diagnostics");return 0;
    }
    if(!battle_mode && !end_mode && !profile_mode) {
        unsigned char plain[72];memset(plain,0xa5,sizeof(plain));
        SetLastError(2468);
        assert(call_maintenance(11,(uintptr_t)(plain+16),33,44,55,2,77,88,99)==plain+16);
        uint32_t code;memcpy(&code,plain+16,4);assert(code==0x57c80000 && !maintenance_forwarded && GetLastError()==2468);
        for(unsigned i=0;i<16;i++)assert(plain[i]==0xa5 && plain[56+i]==0xa5);
        assert(call_maintenance(11,(uintptr_t)(plain+16),33,44,55,3,77,88,99)==(void *)123);
        assert(maintenance_forwarded==1 && GetLastError()==9876);
        FILE *policy=_wfopen(account_policy,L"wb");assert(policy);assert(fwrite("1\n",1,2,policy)==2);fclose(policy);
        ULONGLONG until=GetTickCount64()+1000;while(!ranked_allowed){assert(GetTickCount64()<until);Sleep(5);}
        assert(call_maintenance(11,(uintptr_t)(plain+16),33,44,55,2,77,88,99)==(void *)123);
        assert(maintenance_forwarded==2);
        assert(DeleteFileW(account_policy));until=GetTickCount64()+1000;
        while(ranked_allowed){assert(GetTickCount64()<until);Sleep(5);}
        call_maintenance(11,(uintptr_t)(plain+16),33,44,55,2,77,88,99);assert(maintenance_forwarded==2);
    }
    if(!wcscmp(argv[2],L"bridge") || battle_mode || end_mode || profile_mode) {
        bridge_mode=1;nested=1;
        set_request("https://steam-lb.dbs.channel.or.jp/user/login.php");guarded();
        assert(call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request)==out+16);
        assert(out[16]==2 && projected==1 && released==1 && header_released==1);
        check_guard();assert(job.state==IDLE);
        if(profile_mode) {
            const char *bodies[]={"{\"player_rank\":7,\"auth_info\":\"NEVER-FORWARD\"}",
                "{\"character_id\":\"Goku\",\"character_proficiency_rank\":4,\"auth_info\":\"NEVER-FORWARD\"}"};
            bridge_mode=2;
            for(unsigned i=0;i<2;i++) {
                char url[160];snprintf(url,sizeof(url),"https://szero.invalid%s",routes[10+i]);
                set_request(url);guarded();request[40]=1;
                uintptr_t data=(uintptr_t)bodies[i];uint64_t size=strlen(bodies[i]);
                memcpy(request+48,&data,8);memcpy(request+56,&size,8);memcpy(request+64,&size,8);
                SetLastError(1234);assert(call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request)==out+16);
                assert(GetLastError()==1234 && out[16]==2 && job.state==IDLE);check_guard();
            }
            assert(projected==3 && released==3 && header_released==3);
            assert(DeleteFileW(endpoint));deadline=GetTickCount64()+2000;
            while(state==ARMED || state==STOPPING) {assert(GetTickCount64()<deadline);Sleep(5);}
            assert(state==STOPPED && !memcmp(before,(void *)&fixture_exchange,32));
            assert(!memcmp(before_result,(void *)&fixture_battle_result,32));
            if(quiet_profile)assert(GetFileAttributesW(log_path)==INVALID_FILE_ATTRIBUTES);
            puts("Compiled profile updates and native ownership passed");return 0;
        }
        if(battle_mode || end_mode) {
            bridge_mode=end_mode?4:3;char url[160],body[256];
            snprintf(url,sizeof(url),"https://szero.invalid%s",routes[end_mode?(end_mode==1?8:9):(battle_mode==1?6:7)]);
            set_request(url);guarded();
            request[40]=1;
            if(end_mode || battle_mode==2) {
                assert(argc==4);char code[33];assert(wcslen(argv[3])==32);
                for(unsigned i=0;i<32;i++)code[i]=(char)argv[3][i];
                code[32]=0;
                if(end_mode) {
                    memcpy(result_match_code,code,33);unsigned char actual=(unsigned char)end_mode;
                    assert(call_result(0x4321,(uintptr_t)&actual)==(void *)0xdeadbeef);
                }
                snprintf(body,sizeof(body),"{\"match_code\":\"%s\",\"outcome\":%d,\"auth_info\":\"NEVER-FORWARD\"}",code,end_mode?end_mode:1);
                uintptr_t data=(uintptr_t)body;uint64_t size=strlen(body);
                memcpy(request+48,&data,8);memcpy(request+56,&size,8);memcpy(request+64,&size,8);
            } else {
                uint64_t invalid=UINT64_MAX;
                memcpy(request+48,&invalid,8);memcpy(request+56,&invalid,8);memcpy(request+64,&invalid,8);
            }
            SetLastError(1234);
            assert(call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request)==out+16);
            assert(GetLastError()==1234 && out[16]==2 && job.state==IDLE);check_guard();
            assert(projected==2 && released==2 && header_released==2);
            assert(DeleteFileW(endpoint));deadline=GetTickCount64()+2000;
            while(state==ARMED || state==STOPPING) {assert(GetTickCount64()<deadline);Sleep(5);}
            assert(state==STOPPED && !memcmp(before,(void *)&fixture_exchange,32));
            assert(!memcmp(before_result,(void *)&fixture_battle_result,32));
            puts("Compiled battle-start route and native response ownership passed");return 0;
        }
        bridge_mode=2;
        for(unsigned i=1;i<5;i++) {
            char url[160];snprintf(url,sizeof(url),"https://szero.invalid%s",routes[i]);
            set_request(url);guarded();
            assert(call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request)==out+16);
            assert(out[16]==2 && job.state==IDLE);check_guard();
        }
        assert(projected==5 && released==5 && header_released==5);
        assert(DeleteFileW(endpoint));deadline=GetTickCount64()+2000;
        while(state==ARMED || state==STOPPING) {assert(GetTickCount64()<deadline);Sleep(5);}
        assert(state==STOPPED && !memcmp(before,(void *)&fixture_exchange,32));
            assert(!memcmp(before_result,(void *)&fixture_battle_result,32));
        assert(!memcmp(before_gate,(void *)&fixture_maintenance,32));
        puts("Compiled backend -> real bridge/server LAN login contract passed");return 0;
    }
    set_request("https://other.invalid/user/login.php");guarded();
    SetLastError(4321);
    assert(call_entry(0x9000,(uintptr_t)(out+16),(uintptr_t)request)==(void *)0x9876);
    check_guard();assert(delegated==1);
    set_request("https://steam-lb.dbs.channel.or.jp/user/login.php");guarded();
    InterlockedExchange(&fixture_pause_after_done,1);
    SetLastError(1234);
    assert(call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request)==out+16);
    assert(GetLastError()==1234);check_guard();assert(out[16]==2);
    assert(projected==1 && released==1 && header_released==1 && nested==1);
    assert(job.state==IDLE); /* Must release before return, even with worker paused. */
    HANDLE thread=CreateThread(NULL,0,other_thread,NULL,0,NULL);assert(thread);
    assert(WaitForSingleObject(thread,2000)==WAIT_OBJECT_0);CloseHandle(thread);
    assert(projected==1 && delegated==1);
    set_request("https://steam-lb.dbs.channel.or.jp/unknown.php");guarded();
    call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==1 && output_code()==0x57c80000 && delegated==1);check_guard();
    set_request("https://szero.invalid/user/update_player_rank.php");guarded();
    call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==1 && output_code()==0x57c80000 && delegated==1);check_guard();
    set_request("https://szero.invalid/user/check_transaction.php");guarded();
    call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==1 && output_code()==0x57c80000);check_guard();wait_idle();
    set_request("https://szero.invalid/shop_banner/get_list.php");guarded();
    call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==1 && output_code()==0x57c77900);check_guard();wait_idle();
    assert(projected==2 && released==2 && header_released==2);
    set_request("https://szero.invalid/system/get_notice.php");guarded();cancel_next=1;yields=0;
    call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==1 && output_code()==0x57c80000);check_guard();
    assert(job.state!=IDLE); /* Cancel cannot immediately reuse worker-owned bytes. */
    call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==1);cancel_next=0;wait_idle();
    set_request("https://szero.invalid/user/login.php");guarded();
    call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==2);check_guard();wait_idle();
    assert(projected==3 && released==3 && header_released==3);
    set_request("https://szero.invalid/user/get_player_card.php");
    const char *card_body="{\"session_code\":\"secret-never-forwarded\",\"platform_user_id\":\"szlan:0123456789abcdef0123456789abcdef\"}";
    uint64_t card_size=strlen(card_body);request[40]=1;
    memcpy(request+48,&card_body,8);memcpy(request+56,&card_size,8);memcpy(request+64,&card_size,8);
    guarded();call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==2);check_guard();wait_idle();
    assert(projected==4 && released==4 && header_released==4);
    /* Nonlocal platform identity is refused and never sent to loopback IPC. */
    card_body="{\"platform_user_id\":\"76561198099999999\"}";card_size=strlen(card_body);
    memcpy(request+48,&card_body,8);memcpy(request+56,&card_size,8);memcpy(request+64,&card_size,8);
    guarded();call_entry(service_value,(uintptr_t)(out+16),(uintptr_t)request);
    assert(out[16]==1 && projected==4);check_guard();assert(job.state==IDLE);
    set_request("https://szero.invalid/pvp/start_battle_player1.php");guarded();
    unsigned previous_delegated=delegated;
    assert(call_entry(service_value+1,(uintptr_t)(out+16),(uintptr_t)request)==(void *)0x9876);
    assert(delegated==previous_delegated+1 && job.state==IDLE);check_guard();
    assert(DeleteFileW(endpoint));deadline=GetTickCount64()+2000;
    while(state==ARMED || state==STOPPING) {assert(GetTickCount64()<deadline);Sleep(5);}
    assert(state==STOPPED);assert(!memcmp(before,(void *)&fixture_exchange,32));
    assert(!memcmp(before_result,(void *)&fixture_battle_result,32));
    assert(!memcmp(before_gate,(void *)&fixture_maintenance,32));
    puts("Backend adapter worker, cancellation, ownership, thread and restoration contracts passed");
    return 0;
}
