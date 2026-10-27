/* Scoped original backend exchange -> owned LAN response, never Steam auth.
 * Worker owns sockets/hash/hooks. Known game thread only yields native tasks
 * and projects verified response bytes using original JSON/ownership helpers.
 * DLL and trampolines remain process-pinned for suspended native fibers. */
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#include <ws2tcpip.h>
#include <bcrypt.h>
#include "native_image.h"
#include "native_bindings.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include "backend_response.h"
#include "vendor/minhook/include/MinHook.h"

enum {OFF,VERIFYING,ARMED,STOPPING,STOPPED,FAILED};
enum {IDLE,FILLING,QUEUED,RUNNING,DONE};
static volatile LONG state=OFF;
static struct {
    volatile LONG state,cancel,hook_done;
    char path[96];
    char target[45];
    char match_code[33],rank_snapshot[1024],profile_update[1024];
    int outcome,rank_default,native_category,native_result;
    unsigned char request_scratch[4097];
    unsigned char battle_scratch[65537];
    unsigned char body[SZERO_BACKEND_BODY_MAX];
    size_t size;
    int ok;
} job;
static uintptr_t image_base,entry,pinned_service;
static unsigned char installed_prefix[16];
static uintptr_t battle_result_entry;
static unsigned char battle_result_installed[16];
static void *(*original_battle_result)(uintptr_t,uintptr_t);
static const unsigned char battle_result_prefix[16]={
    0x48,0x89,0x5c,0x24,0x10,0x57,0x48,0x83,0xec,0x50,0x0f,0x10,0x81,0x60,0x13,0x00};
/* Game-thread-owned epoch. Result setters outside an issued round cannot rate it. */
static char result_match_code[33];
static unsigned result_value,result_sealed;

static DWORD game_thread;
static wchar_t endpoint[32768],log_path[32768],account_policy[32768];
static volatile LONG ranked_allowed;
static int account_mode;
enum {CARD_BODY=1,CARD_JSON,CARD_REMOTE_ID,CARD_LOCAL_CONTEXT,CARD_LOCAL_MISMATCH,
    REQUEST_SCOPE,REQUEST_BUSY,REQUEST_THREAD,RANK_UPDATE_ROUTE,PROFICIENCY_UPDATE_ROUTE,
    CARD_UPDATE_ROUTE,BATTLE_BINDING,BATTLE_BODY,BATTLE_JSON,RANK_SNAPSHOT,REFUSAL_COUNT};
static volatile LONG refusals[REFUSAL_COUNT];
static const char *const refusal_names[REFUSAL_COUNT]={"none","card_body_unreadable",
    "card_json_invalid","card_remote_identity_invalid","card_local_context_unavailable",
    "card_local_identity_mismatch","request_scope","request_busy","request_thread",
    "unsupported_rank_update_route","unsupported_proficiency_update_route","unsupported_card_update_route",
    "battle_start_foreign_or_unbound_service","battle_body_unreadable",
    "battle_report_invalid","native_rank_snapshot_unavailable"};
static void refused(unsigned reason) {
    if(reason>0 && reason<REFUSAL_COUNT)InterlockedIncrement(refusals+reason);
}
static uintptr_t maintenance_entry;
static unsigned char maintenance_installed[16];
static void *(*original_maintenance)(uintptr_t,uintptr_t,uintptr_t,uintptr_t,uintptr_t,
    uintptr_t,uintptr_t,uintptr_t,uintptr_t);
static const unsigned char maintenance_prefix[16]={
    0x40,0x55,0x53,0x56,0x57,0x41,0x55,0x41,0x56,0x48,0x8d,0xac,0x24,0x88,0xfc,0xff};
static char instance[33];
static void *(*original_exchange)(uintptr_t,uintptr_t,uintptr_t);
static void *(*current_task)(void);
static unsigned char (*yield_cancel)(void *);
static void *(*native_factory)(uintptr_t,SzeroBackendView **);
static void (*native_project)(void *,SzeroBackendRaw *);
static void (*native_release_stream)(SzeroBackendOwner *);
static void (*native_release_headers)(SzeroBackendHeaders *);
static uintptr_t (*native_rank_category)(uintptr_t);
static const uintptr_t offsets[]={0x5a9c800,0x591c800,0x593dbb0,0x228bab0,
    0x58ac920,0x5817fe0,0x5818a50,0x5a77090};
static const unsigned char prefixes[][16]={
 {0x40,0x55,0x53,0x56,0x57,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x8d,0xac,0x24,0xc0},
 {0x48,0x89,0x5c,0x24,0x08,0x57,0x48,0x83,0xec,0x20,0x48,0x8b,0x3d,0xef,0xb0,0x3d},
 {0x48,0x89,0x5c,0x24,0x20,0x55,0x57,0x41,0x54,0x41,0x56,0x41,0x57,0x48,0x8d,0xac},
 {0x40,0x53,0x48,0x83,0xec,0x20,0x48,0x8b,0x59,0x08,0x48,0x85,0xdb,0x74,0x5d,0x48},
 {0x48,0x83,0xec,0x28,0x48,0x89,0x5c,0x24,0x38,0x48,0x8b,0x59,0x18,0x4c,0x89,0x74},
 {0x40,0x55,0x48,0x8d,0x6c,0x24,0xa9,0x48,0x81,0xec,0xa0,0,0,0,0x48,0x8b},
 {0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x20,0x80},
 {0x40,0x53,0x48,0x83,0xec,0x20,0x48,0x8b,0xd9,0xe8,0x92,0x6a,0xe4,0xff,0x84,0xc0}};
#ifdef SZERO_BACKEND_ADAPTER_TEST
static uintptr_t fixture_entry;
static uintptr_t fixture_rank_backend;
static volatile LONG fixture_pause_after_done,fixture_done_reached,fixture_endpoint_seen;
#endif
static const char *const routes[]={"/user/login.php","/user/check_transaction.php",
    "/system/get_notice.php","/pvp/get_report_taken_counts.php","/shop_banner/get_list.php",
    "/user/get_player_card.php","/pvp/start_battle_player1.php",
    "/pvp/start_battle_player2.php","/pvp/end_battle_player1.php",
    "/pvp/end_battle_player2.php","/user/update_player_rank.php",
    "/user/update_proficiency_rank.php"};
static int read_mem(uintptr_t p,void *out,size_t n) {
    SIZE_T got=0;
    return p && n<=UINTPTR_MAX-p &&
        ReadProcessMemory(GetCurrentProcess(),(void *)p,out,n,&got) && got==n;
}
static void *capture_battle_result(uintptr_t object,uintptr_t borrowed) {
    DWORD error=GetLastError();unsigned char value=0;int readable=0;
    int capture=state==ARMED && GetCurrentThreadId()==game_thread && result_match_code[0] && !result_sealed;
    if(capture)readable=read_mem(borrowed,&value,1);
    SetLastError(error);void *result=original_battle_result(object,borrowed);
    error=GetLastError();
    if(capture)result_value=readable && value>=1 && value<=3?value:0;
    SetLastError(error);return result;
}
static void accept_battle_start(const unsigned char *body,size_t size);
static void *unavailable(uintptr_t out) {
    /* Original tagged-error shape:1 + zero40B error, code57C80000 at+8.
     * No claimed successful service/login/result is manufactured. */
    unsigned char bytes[48]={0};uint32_t tag=1,code=0x57c80000;
    memcpy(bytes,&tag,4);memcpy(bytes+8,&code,4);
    SIZE_T written=0;
    if(out && out<=UINTPTR_MAX-sizeof(bytes))
        WriteProcessMemory(GetCurrentProcess(),(void *)out,bytes,sizeof(bytes),&written);
    return (void *)out;
}
static void *fail_result(uintptr_t out,DWORD error) {
    void *result=unavailable(out);SetLastError(error);return result;
}
static void *delegate(uintptr_t service,uintptr_t out,uintptr_t request,DWORD error) {
    SetLastError(error);return original_exchange(service,out,request);
}
/* Category2 is the recovered Ranked maintenance gate. Other maintenance and
 * platform/authentication checks retain their original arguments and result.
 * This is a cooperative UI gate; the server independently verifies account
 * tokens and authorizes ranked service operations. Never grants native success. */
static void *maintenance(uintptr_t a,uintptr_t out,uintptr_t c,uintptr_t d,uintptr_t e,
    uintptr_t category,uintptr_t g,uintptr_t h,uintptr_t i) {
    DWORD error=GetLastError();
    if(account_mode && GetCurrentThreadId()==game_thread && (unsigned char)category==2 &&
       !InterlockedCompareExchange(&ranked_allowed,0,0)) {
        unsigned char plain[40]={0};uint32_t code=0x57c80000;SIZE_T written=0;
        memcpy(plain,&code,4);
        if(out && out<=UINTPTR_MAX-sizeof(plain))
            WriteProcessMemory(GetCurrentProcess(),(void *)out,plain,sizeof(plain),&written);
        SetLastError(error);return (void *)out;
    }
    SetLastError(error);return original_maintenance(a,out,c,d,e,category,g,h,i);
}
static int read_ranked_policy(void) {
    char bytes[3];FILE *file=_wfopen(account_policy,L"rb");
    if(!file)return 0;
    size_t n=fread(bytes,1,sizeof(bytes),file);int extra=fgetc(file);fclose(file);
    return n==2 && extra==EOF && bytes[0]=='1' && bytes[1]=='\n';
}
static int native_text(uintptr_t source,unsigned char *output,size_t capacity,size_t *length) {
    unsigned char value[32];uint64_t size,allocated;uintptr_t data;
    if(!read_mem(source,value,sizeof(value)))return 0;
    if(value[0]&1) {
        memcpy(&data,value+8,8);memcpy(&size,value+16,8);memcpy(&allocated,value+24,8);
        if(size>allocated)return 0;
    } else {data=source+1;size=value[0]>>2;if(size>((value[0]&2)?22u:30u))return 0;}
    if(size>=capacity || (size && !read_mem(data,output,(size_t)size)))return 0;
    output[size]=0;*length=(size_t)size;return !memchr(output,0,(size_t)size);
}
typedef struct {const unsigned char *p,*end;} JsonCursor;
static void json_space(JsonCursor *c) {while(c->p<c->end && (*c->p==' ' || *c->p=='\n' || *c->p=='\r' || *c->p=='\t'))c->p++;}
static int json_string(JsonCursor *c,char *out,size_t cap) {
    size_t used=0;int fits=1;
    if(c->p==c->end || *c->p++!='"')return 0;
    while(c->p<c->end) {
        unsigned ch=*c->p++;
        if(ch=='"') {if(out && cap)out[used<cap?used:cap-1]=0;return fits?1:2;}
        if(ch<32)return 0;
        if(ch=='\\') {
            if(c->p==c->end)return 0;
            ch=*c->p++;
            if(ch=='u') {
                ch=0;
                for(unsigned i=0;i<4;i++) {
                    if(c->p==c->end)return 0;
                    unsigned x=*c->p++;
                    if(x>='0'&&x<='9')x-='0';else if(x>='a'&&x<='f')x=x-'a'+10;
                    else if(x>='A'&&x<='F')x=x-'A'+10;else return 0;
                    ch=(ch<<4)|x;
                }
                if(ch>127 || !ch)fits=0;
            } else if(ch=='b')ch=8;else if(ch=='f')ch=12;else if(ch=='n')ch=10;
            else if(ch=='r')ch=13;else if(ch=='t')ch=9;
            else if(ch!='"'&&ch!='\\'&&ch!='/')return 0;
        }
        if(out) {if(used+1<cap)out[used]=(char)ch;else fits=0;}
        used++;
    }
    return 0;
}
static int json_skip(JsonCursor *c,unsigned depth) {
    if(depth>8)return 0;
    json_space(c);if(c->p==c->end)return 0;
    if(*c->p=='"')return json_string(c,NULL,0)!=0;
    if(*c->p=='{' || *c->p=='[') {
        int object=*c->p++=='{';unsigned char close=object?'}':']';json_space(c);
        if(c->p<c->end && *c->p==close){c->p++;return 1;}
        for(;;) {
            if(object) {if(!json_string(c,NULL,0))return 0;json_space(c);
                if(c->p==c->end || *c->p++!=':')return 0;}
            if(!json_skip(c,depth+1))return 0;
            json_space(c);
            if(c->p==c->end)return 0;
            if(*c->p==close){c->p++;return 1;}
            if(*c->p++!=',')return 0;
            json_space(c);
        }
    }
    const unsigned char *start=c->p;
    while(c->p<c->end && !strchr(" ,]}\r\n\t",*c->p))c->p++;
    size_t n=(size_t)(c->p-start);
    if((n==4&&(!memcmp(start,"true",4)||!memcmp(start,"null",4))) ||
       (n==5&&!memcmp(start,"false",5)))return 1;
    JsonCursor num={start,c->p};
    if(num.p<num.end&&*num.p=='-')num.p++;
    if(num.p==num.end || *num.p<'0' || *num.p>'9')return 0;
    if(*num.p=='0')num.p++;else while(num.p<num.end&&*num.p>='0'&&*num.p<='9')num.p++;
    if(num.p<num.end&&*num.p=='.') {num.p++;start=num.p;while(num.p<num.end&&*num.p>='0'&&*num.p<='9')num.p++;if(num.p==start)return 0;}
    if(num.p<num.end&&(*num.p=='e'||*num.p=='E')) {num.p++;if(num.p<num.end&&(*num.p=='+'||*num.p=='-'))num.p++;start=num.p;while(num.p<num.end&&*num.p>='0'&&*num.p<='9')num.p++;if(num.p==start)return 0;}
    return num.p==num.end;
}
static int card_target(const unsigned char *body,size_t size,char target[65]) {
    JsonCursor c={body,body+size};unsigned found=0;json_space(&c);
    if(c.p==c.end||*c.p++!='{')return 0;
    json_space(&c);
    while(c.p<c.end && *c.p!='}') {
        char key[32];int key_ok=json_string(&c,key,sizeof(key));if(!key_ok)return 0;
        json_space(&c);if(c.p==c.end||*c.p++!=':')return 0;json_space(&c);
        if(key_ok==1 && !strcmp(key,"platform_user_id")) {
            if(found++ || json_string(&c,target,65)!=1)return 0;
        } else if(!json_skip(&c,0))return 0;
        json_space(&c);if(c.p==c.end)return 0;
        if(*c.p=='}')break;
        if(*c.p++!=',')return 0;
        json_space(&c);
        if(c.p==c.end||*c.p=='}')return 0;
    }
    if(c.p==c.end||*c.p++!='}')return 0;
    json_space(&c);
    return c.p==c.end && found==1 && target[0];
}
/* Approved finish DTO, never a copied native JSON envelope. */
static int battle_values(const unsigned char *body,size_t size,int need_outcome,char code[33],int *outcome) {
    JsonCursor c={body,body+size};unsigned codes=0,outcomes=0;int value=-1;
    json_space(&c);if(c.p==c.end||*c.p++!='{')return 0;json_space(&c);
    while(c.p<c.end && *c.p!='}') {
        char key[32];int key_ok=json_string(&c,key,sizeof(key));if(!key_ok)return 0;
        json_space(&c);if(c.p==c.end||*c.p++!=':')return 0;json_space(&c);
        if(key_ok==1 && !strcmp(key,"match_code")) {
            if(codes++ || json_string(&c,code,33)!=1)return 0;
        } else if(need_outcome && key_ok==1 && !strcmp(key,"outcome")) {
            if(outcomes++ || c.p==c.end || (*c.p!='1' && *c.p!='2'))return 0;
            value=*c.p++-'0';
        } else if(!json_skip(&c,0))return 0;
        json_space(&c);if(c.p==c.end)return 0;
        if(*c.p=='}')break;
        if(*c.p++!=',')return 0;
        json_space(&c);
        if(c.p==c.end||*c.p=='}')return 0;
    }
    if(c.p==c.end||*c.p++!='}')return 0;
    json_space(&c);
    if(c.p!=c.end || codes!=1 || strlen(code)!=32 || (need_outcome && outcomes!=1))return 0;
    for(unsigned i=0;i<32;i++)if(!((code[i]>='0'&&code[i]<='9')||(code[i]>='a'&&code[i]<='f')))return 0;
    *outcome=value;return 1;
}
/* Copy only recovered profile fields, never the native auth envelope. */
static int profile_values(const unsigned char *body,size_t size,int proficiency,char output[1024]) {
    JsonCursor c={body,body+size};unsigned seen=0;size_t used=1;output[0]='{';
    json_space(&c);if(c.p==c.end || *c.p++!='{')return 0;json_space(&c);
    while(c.p<c.end && *c.p!='}') {
        char key[64];int key_ok=json_string(&c,key,sizeof(key));if(!key_ok)return 0;
        json_space(&c);if(c.p==c.end || *c.p++!=':')return 0;json_space(&c);
        const unsigned char *start=c.p;unsigned bit=0;
        if(key_ok==1 && !strcmp(key,proficiency?"character_proficiency_rank":"player_rank"))bit=1;
        if(proficiency && key_ok==1 && !strcmp(key,"character_id"))bit=2;
        if(!json_skip(&c,0))return 0;
        if(bit) {
            if(seen&bit)return 0;
            seen|=bit;
            size_t n=(size_t)(c.p-start),k=strlen(key);
            if(used+n+k+6>=1024)return 0;
            if(used>1)output[used++]=',';
            output[used++]='"';memcpy(output+used,key,k);used+=k;
            output[used++]='"';output[used++]=':';memcpy(output+used,start,n);used+=n;
        }
        json_space(&c);if(c.p==c.end)return 0;if(*c.p=='}')break;
        if(*c.p++!=',')return 0;
        json_space(&c);if(c.p==c.end || *c.p=='}')return 0;
    }
    if(c.p==c.end || *c.p++!='}')return 0;
    json_space(&c);
    if(c.p!=c.end || seen!=(proficiency?3u:1u))return 0;
    output[used++]='}';output[used]=0;return 1;
}
static int normalize_profile_values(uintptr_t request,int proficiency) {
    size_t n=0;int ok=0;
    if(request<=UINTPTR_MAX-0x28 && native_text(request+0x28,job.battle_scratch,sizeof(job.battle_scratch),&n))
        ok=profile_values(job.battle_scratch,n,proficiency,job.profile_update);
    SecureZeroMemory(job.battle_scratch,sizeof(job.battle_scratch));
    if(!ok)refused(BATTLE_JSON);
    return ok;
}
static void accept_battle_start(const unsigned char *body,size_t size) {
    char code[33];int ignored;
    if(battle_values(body,size,0,code,&ignored) && strcmp(code,result_match_code)) {
        memcpy(result_match_code,code,sizeof(result_match_code));result_value=0;result_sealed=0;
    }
}
static int quote_rank_title(const unsigned char *text,size_t size,char output[769]) {
    size_t n=0;
    for(size_t i=0;i<size;i++) {
        unsigned ch=text[i];
        if(ch<32 || ch==127)return 0;
        if(ch=='"' || ch=='\\')output[n++]='\\';
        output[n++]=(char)ch;
    }
    output[n]=0;return 1;
}
static int rank_snapshot_cache(uintptr_t backend,unsigned category,unsigned extra,char output[1024]) {
    uintptr_t records=0,selected=0;uint64_t count=0;unsigned char node[64];
    unsigned lookup=category==1?1:(category==2||category==3)?2:0;
    if(!lookup || backend>UINTPTR_MAX-0x100 ||
       !read_mem(backend+0xf0,&records,8) || !read_mem(backend+0xf8,&count,8) ||
       count>32 || (count && (!records || count>(UINTPTR_MAX-records)/64)))return 0;
    for(uint64_t i=0;i<count;i++) {
        uintptr_t at=records+(uintptr_t)i*64;
        if(!read_mem(at,node,sizeof(node)))return 0;
        if(node[0x35]==lookup && node[0x36]==extra) {
            if(selected)return 0; /* Multiple extra-types: refuse ambiguous selection. */
            selected=at;
        }
    }
    unsigned char title[129]={0};char escaped[769];size_t title_size=0;
    if(selected) {
        if(!read_mem(selected,node,sizeof(node)) || !native_text(selected,title,sizeof(title),&title_size))return 0;
    } else {
        /* Exact145ad7410 missing-entry constructor: zero record, then RAW
         * category+35 and extra+36. No unrelated cache entry is overwritten. */
        memset(node,0,sizeof(node));node[0x35]=(unsigned char)category;node[0x36]=(unsigned char)extra;
    }
    if(!quote_rank_title(title,title_size,escaped))return 0;
    int32_t point,previous,next;uint32_t streak,bits;
    memcpy(&point,node+0x20,4);memcpy(&previous,node+0x24,4);memcpy(&next,node+0x28,4);
    memcpy(&streak,node+0x2c,4);memcpy(&bits,node+0x30,4);
    if((bits&0x7f800000u)==0x7f800000u)return 0;
    int n=snprintf(output,1024,"{\"rank_title\":\"%s\",\"rank_point\":%ld,\"prev_need_point\":%ld,\"next_need_point\":%ld,"
        "\"win_streak\":%lu,\"win_streak_r_bits\":%lu,\"app_multiplayer_mode\":%u,\"battle_type\":%u,"
        "\"pvp_extra_type\":%u,\"rank_range\":%d,\"rank\":%d}",escaped,(long)point,(long)previous,(long)next,
        (unsigned long)streak,(unsigned long)bits,node[0x34],node[0x35],node[0x36],(int)(int8_t)node[0x37],(int)(int8_t)node[0x38]);
    return n>0 && n<1024?(selected?1:2):0;
}
static int capture_rank_snapshot(void) {
#ifdef SZERO_BACKEND_ADAPTER_TEST
    job.native_category=1;
    int rc=rank_snapshot_cache(fixture_rank_backend,1,0,job.rank_snapshot);
    job.rank_default=rc==2;return rc!=0;
#else
    uintptr_t context=0,vtable=0,session=0,backend=0;
    if(!native_rank_category || !read_mem(image_base+szero_bind_rva(0x8cf84f8),&context,8) || !context ||
       context>UINTPTR_MAX-0x48 || !read_mem(context,&vtable,8) || vtable!=image_base+szero_bind_rva(0x7ba1bf8) ||
       !read_mem(context+0x40,&session,8) || !session ||
       !read_mem(image_base+szero_bind_rva(0x87010e8),&backend,8) || !backend)return 0;
    uintptr_t members=0;uint64_t count=0;unsigned found=0,extra=0;
    if(session>UINTPTR_MAX-0x28 || !read_mem(session+0x18,&members,8) ||
       !read_mem(session+0x20,&count,8) || !count || count>8 || !members || count>(UINTPTR_MAX-members)/8)return 0;
    for(uint64_t i=0;i<count;i++) {
        uintptr_t member=0,descriptor=0;unsigned char local=0,data[2];
        if(!read_mem(members+(uintptr_t)i*8,&member,8) || !member || member>UINTPTR_MAX-0x10c ||
           !read_mem(member+8,&descriptor,8) || !descriptor || descriptor>UINTPTR_MAX-0x8c ||
           !read_mem(descriptor+0x8b,&local,1))return 0;
        if(local==1) {
            if(found++ || !read_mem(member+0x10a,data,2))return 0;
            extra=data[0] && data[1]>1;
        }
    }
    if(found!=1)return 0;
    unsigned category=(unsigned char)native_rank_category(context);
    job.native_category=(int)category;
    int rc=rank_snapshot_cache(backend,category,extra,job.rank_snapshot);
    job.rank_default=rc==2;return rc!=0;
#endif
}
static int normalize_battle_values(uintptr_t request,int ending) {
    size_t size=0;int ok=0;
    if(request>UINTPTR_MAX-0x28 || !native_text(request+0x28,job.battle_scratch,
        sizeof(job.battle_scratch),&size)) {refused(BATTLE_BODY);goto done;}
    if(!battle_values(job.battle_scratch,size,ending,job.match_code,&job.outcome)) {
        refused(BATTLE_JSON);goto done;
    }
    if(ending && !capture_rank_snapshot()) {refused(RANK_SNAPSHOT);goto done;}
    if(ending && !strcmp(result_match_code,job.match_code)) {
        job.native_result=(int)result_value;
        if(job.native_result)result_sealed=1;
    }
    ok=1;
done:
    SecureZeroMemory(job.battle_scratch,sizeof(job.battle_scratch));return ok;
}
static int normalize_card_target(uintptr_t request,char output[45]) {
    size_t size=0;char target[65];int ok=0;
    if(request>UINTPTR_MAX-0x28 || !native_text(request+0x28,job.request_scratch,
        sizeof(job.request_scratch),&size)) {refused(CARD_BODY);goto done;}
    if(!card_target(job.request_scratch,size,target)) {refused(CARD_JSON);goto done;}
    size=strlen(target);
    if(size==38 && !memcmp(target,"szlan:",6)) {
        for(unsigned i=6;i<38;i++)if(!((target[i]>='0'&&target[i]<='9') ||
            (target[i]>='a'&&target[i]<='f'))) {refused(CARD_REMOTE_ID);goto done;}
        memcpy(output,target,39);ok=1;goto done;
    }
    uintptr_t context=0,vptr=0,bundle=0,user=0;unsigned char local[65];size_t local_size=0;
    if(read_mem(image_base+szero_bind_rva(0x8cf84f8),&context,8) && read_mem(context,&vptr,8) &&
       vptr==image_base+szero_bind_rva(0x7ba1bf8) && context<=UINTPTR_MAX-8 &&
       read_mem(context+8,&bundle,8) && bundle<=UINTPTR_MAX-0x18 &&
       read_mem(bundle+0x18,&user,8) && user<=UINTPTR_MAX-0x200 &&
       native_text(user+0x200,local,sizeof(local),&local_size)) {
        if(local_size==size && !memcmp(local,target,size)) {memcpy(output,"self",5);ok=1;}
        else refused(CARD_LOCAL_MISMATCH);
    } else refused(CARD_LOCAL_CONTEXT);
done:
    SecureZeroMemory(job.request_scratch,sizeof(job.request_scratch));return ok;
}
/* Return known route index, -1 not our URL, -2 malformed/unknown claimed URL.
 * -3..-5 name exact known but UNSUPPORTED routes for refusal diagnostics only. */
static int request_route(uintptr_t request,char path[96]) {
    unsigned char string[32];char url[1025];uintptr_t data;uint64_t size;
    if(!read_mem(request,string,sizeof(string))) return -2;
    if(string[0]&1) {
        uint64_t capacity;memcpy(&data,string+8,8);memcpy(&size,string+16,8);
        memcpy(&capacity,string+24,8);if(size>capacity) return -2;
    } else {
        data=request+1;size=string[0]>>2;
        if(size>((string[0]&2)?22u:30u)) return -2;
    }
    if(!size || size>1024 || !read_mem(data,url,(size_t)size)) return -2;
    url[size]=0;
    if(memchr(url,0,(size_t)size)) return -2;
    const char *suffix=NULL;
    const char *base="https://steam-lb.dbs.channel.or.jp";
    size_t n=strlen(base);
    if(!strncmp(url,base,n) && url[n]=='/') suffix=url+n;
    base="https://szero.invalid";n=strlen(base);
    if(!suffix && !strncmp(url,base,n) && url[n]=='/') suffix=url+n;
    if(!suffix) return -1;
    for(size_t i=0;i<sizeof(routes)/sizeof(routes[0]);++i) if(!strcmp(suffix,routes[i])) {
        memcpy(path,routes[i],strlen(routes[i])+1);return (int)i;
    }
    if(!strcmp(suffix,"/user/update_player_card.php"))return -5;
    return -2;
}
static SzeroBackendView *create_view(void *unused) {
    (void)unused;SzeroBackendView *view=NULL;
    native_factory(0,&view);
    if(view && view->vtable!=image_base+szero_bind_rva(0x6d36f80)) {
        /* Do not call an unknown object's destructor. Quarantine this helper;
         * retaining one unexpected allocation is safer than dispatching it. */
        InterlockedExchange(&state,FAILED);return NULL;
    }
    return view;
}
static void project(void *unused,void *out,SzeroBackendRaw *raw) {
    (void)unused;native_project(out,raw);
}
static void release_stream(void *unused,SzeroBackendOwner *owner) {
    (void)unused;native_release_stream(owner);
}
static void release_headers(void *unused,SzeroBackendHeaders *headers) {
    (void)unused;native_release_headers(headers);
}
static void *exchange(uintptr_t service,uintptr_t out,uintptr_t request) {
    DWORD error=GetLastError();char path[96];
    if(GetCurrentThreadId()!=game_thread) {
        if(service==pinned_service && pinned_service) {refused(REQUEST_THREAD);return fail_result(out,error);}
        return delegate(service,out,request,error);
    }
    int route=request_route(request,path);
    if(route>=6 && route<=9 && (!pinned_service || service!=pinned_service)) refused(BATTLE_BINDING);
    if(!pinned_service) {
        if(route!=0 || state!=ARMED) return delegate(service,out,request,error);
        if(!service) return fail_result(out,error);
        pinned_service=service;
    }
    if(service!=pinned_service) return delegate(service,out,request,error);
    if(state!=ARMED || route<0) {
        unsigned reason=route==-3?RANK_UPDATE_ROUTE:route==-4?PROFICIENCY_UPDATE_ROUTE:
            route==-5?CARD_UPDATE_ROUTE:REQUEST_SCOPE;
        refused(reason);return fail_result(out,error);
    }
    void *task=current_task();
    if(!task || InterlockedCompareExchange(&job.state,FILLING,IDLE)!=IDLE) {
        refused(REQUEST_BUSY);
        return fail_result(out,error);
    }
    job.profile_update[0]=0;job.target[0]=0;job.match_code[0]=0;job.rank_snapshot[0]=0;job.outcome=-1;job.rank_default=0;job.native_category=0;job.native_result=0;
    if(route==5 && !normalize_card_target(request,job.target)) {
        InterlockedExchange(&job.state,IDLE);return fail_result(out,error);
    }
    if((route==7 || route==8 || route==9) && !normalize_battle_values(request,route>=8)) {
        InterlockedExchange(&job.state,IDLE);return fail_result(out,error);
    }
    if(route>=10 && !normalize_profile_values(request,route==11)) {
        InterlockedExchange(&job.state,IDLE);return fail_result(out,error);
    }
    memcpy(job.path,path,strlen(path)+1);job.size=0;job.ok=0;
    InterlockedExchange(&job.cancel,0);InterlockedExchange(&job.hook_done,0);
    InterlockedExchange(&job.state,QUEUED);
    ULONGLONG start=GetTickCount64();
    for(;;) {
        if(yield_cancel(task) || GetTickCount64()-start>15000 || state!=ARMED) {
            InterlockedExchange(&job.cancel,1);
            InterlockedExchange(&job.hook_done,1);
            return fail_result(out,error);
        }
        if(InterlockedCompareExchange(&job.state,DONE,DONE)==DONE) break;
    }
    if(job.ok) {
        if(route==6 || route==7)accept_battle_start(job.body,job.size);
        SzeroBackendResponseFunctions f={NULL,create_view,project,release_stream,release_headers};
        if(!szero_backend_response_project((void *)out,72,job.body,job.size,&f)) unavailable(out);
    } else unavailable(out);
    InterlockedExchange(&job.hook_done,1);
    /* DONE means worker I/O/logging finished. Projection/cleanup above is the
     * last reader of its bytes. Release BEFORE returning: native continuations
     * can submit the next request immediately, without another worker poll. */
    InterlockedCompareExchange(&job.state,IDLE,DONE);
    SetLastError(error);return (void *)out;
}
static int sha256(const wchar_t *path,char hex[65]) {
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,NULL,OPEN_EXISTING,0,NULL);
    BCRYPT_ALG_HANDLE alg=NULL;BCRYPT_HASH_HANDLE hash=NULL;
    unsigned char buffer[65536],digest[32];DWORD n;int ok=0;
    if(file==INVALID_HANDLE_VALUE) return 0;
    if(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,NULL,0)<0 ||
        BCryptCreateHash(alg,&hash,NULL,0,NULL,0,0)<0) goto done;
    for(;;) {
        if(!ReadFile(file,buffer,sizeof(buffer),&n,NULL)) goto done;
        if(!n) break;
        if(BCryptHashData(hash,buffer,n,0)<0) goto done;
    }
    if(BCryptFinishHash(hash,digest,32,0)<0) goto done;
    for(unsigned i=0;i<32;++i) sprintf(hex+2*i,"%02x",digest[i]);
    ok=1;
done:
    if(hash) BCryptDestroyHash(hash);
    if(alg) BCryptCloseAlgorithmProvider(alg,0);
    CloseHandle(file);return ok;
}
static unsigned read_port(void) {
    FILE *file=_wfopen(endpoint,L"rb");char text[8];size_t n;unsigned port=0;
    if(!file) return 0;
    n=fread(text,1,sizeof(text),file);int extra=fgetc(file);fclose(file);
    if(n<2 || n>6 || extra!=EOF || text[n-1]!='\n') return 0;
    for(size_t i=0;i<n-1;++i) {
        if(text[i]<'0' || text[i]>'9') return 0;
        port=port*10+(unsigned)(text[i]-'0');
    }
    return port>0 && port<=65535?port:0;
}
static int socket_wait(SOCKET socket_fd,int writing,ULONGLONG deadline) {
    while(!job.cancel && GetTickCount64()<deadline) {
        fd_set selected;FD_ZERO(&selected);FD_SET(socket_fd,&selected);
        struct timeval timeout={0,50000};
        int result=select(0,writing?NULL:&selected,writing?&selected:NULL,NULL,&timeout);
        if(result<0) return 0;
        if(result>0) return 1;
    }
    return 0;
}
static int send_all(SOCKET socket_fd,const char *data,size_t size,ULONGLONG deadline) {
    while(size && socket_wait(socket_fd,1,deadline)) {
        int n=send(socket_fd,data,(int)size,0);
        if(n==SOCKET_ERROR && WSAGetLastError()==WSAEWOULDBLOCK) continue;
        if(n<=0) return 0;
        data+=n;size-=(size_t)n;
    }
    return size==0;
}
static int receive_exact(SOCKET socket_fd,char *data,size_t size,ULONGLONG deadline) {
    size_t used=0;
    while(used<size && socket_wait(socket_fd,0,deadline)) {
        int n=recv(socket_fd,data+used,(int)(size-used),0);
        if(n==SOCKET_ERROR && WSAGetLastError()==WSAEWOULDBLOCK) continue;
        if(n<=0) return 0;
        used+=(size_t)n;
    }
    return used==size;
}
static int receive_line(SOCKET socket_fd,char *line,size_t capacity,ULONGLONG deadline) {
    size_t used=0;
    while(used+1<capacity) {
        char c;if(!receive_exact(socket_fd,&c,1,deadline)) return 0;
        line[used++]=c;if(c=='\n') {line[used]=0;return 1;}
    }
    return 0;
}
static int transact(void) {
    unsigned port=read_port();if(!port || job.cancel) return 0;
    SOCKET socket_fd=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(socket_fd==INVALID_SOCKET) return 0;
    ULONGLONG deadline=GetTickCount64()+8000;
    u_long nonblocking=1;
    if(ioctlsocket(socket_fd,FIONBIO,&nonblocking)) {closesocket(socket_fd);return 0;}
    struct sockaddr_in address;memset(&address,0,sizeof(address));
    address.sin_family=AF_INET;address.sin_port=htons((u_short)port);
    address.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    int ok=0;char line[4096],snapshot[2049];
    if(connect(socket_fd,(struct sockaddr *)&address,sizeof(address))) {
        if(WSAGetLastError()!=WSAEWOULDBLOCK || !socket_wait(socket_fd,1,deadline)) goto done;
        int socket_error=0,error_size=sizeof(socket_error);
        if(getsockopt(socket_fd,SOL_SOCKET,SO_ERROR,(char *)&socket_error,&error_size) || socket_error) goto done;
    }
    int length;
    if(job.profile_update[0]) {
        static const char hex[]="0123456789abcdef";size_t n=strlen(job.profile_update);
        for(size_t i=0;i<n;i++) {unsigned char c=(unsigned char)job.profile_update[i];snapshot[2*i]=hex[c>>4];snapshot[2*i+1]=hex[c&15];}
        snapshot[2*n]=0;
        length=snprintf(line,sizeof(line),"SERVICE4 %s %s %s\n",instance,job.path,snapshot);
    } else if(job.match_code[0]) {
        if(job.rank_snapshot[0]) {
            static const char hex[]="0123456789abcdef";size_t n=strlen(job.rank_snapshot);
            for(size_t i=0;i<n;i++) {unsigned char c=(unsigned char)job.rank_snapshot[i];snapshot[2*i]=hex[c>>4];snapshot[2*i+1]=hex[c&15];}
            snapshot[2*n]=0;
            length=snprintf(line,sizeof(line),"SERVICE5 %s %s %s %d %d %d %s\n",instance,job.path,job.match_code,job.outcome,job.native_category,job.native_result,snapshot);
        } else length=snprintf(line,sizeof(line),"SERVICE3 %s %s %s - -\n",instance,job.path,job.match_code);
    } else length=job.target[0]?snprintf(line,sizeof(line),"SERVICE2 %s %s %s\n",instance,job.path,job.target):
        snprintf(line,sizeof(line),"SERVICE1 %s %s\n",instance,job.path);
    if(length<=0 || (size_t)length>=sizeof(line) ||
        !send_all(socket_fd,line,(size_t)length,deadline) || !receive_line(socket_fd,line,16,deadline)) goto done;
    size_t size=0,n=strlen(line);
    if(n<2 || n>6 || line[n-1]!='\n') goto done;
    for(size_t i=0;i<n-1;++i) {
        if(line[i]<'0' || line[i]>'9') goto done;
        size=size*10+(size_t)(line[i]-'0');
    }
    if(!size || size>SZERO_BACKEND_BODY_MAX) goto done;
    if(!receive_exact(socket_fd,(char *)job.body,size,deadline)) goto done;
    job.size=size;ok=1;
done:
    closesocket(socket_fd);return ok;
}
static void log_event(FILE *log,const char *event) {
    SYSTEMTIME now;GetSystemTime(&now);
    fprintf(log,"{\"event\":\"%s\",\"time_utc\":\"%04u-%02u-%02uT%02u:%02u:%02u.%03uZ\"",
        event,now.wYear,now.wMonth,now.wDay,now.wHour,now.wMinute,now.wSecond,now.wMilliseconds);
}
static void flush_refusals(FILE *log,unsigned *logged) {
    if(!log || *logged>=128)return;
    for(unsigned i=1;i<REFUSAL_COUNT && *logged<128;i++) {
        LONG count=InterlockedExchange(refusals+i,0);
        if(count>0) {
            log_event(log,"refusal");
            fprintf(log,",\"reason\":\"%s\",\"count\":%ld}\n",refusal_names[i],count);
            ++*logged;fflush(log);
        }
    }
}
static DWORD WINAPI worker(void *unused) {
    (void)unused;wchar_t path[32768];unsigned char bytes[16];
    int result_enabled=0;
    int gate_enabled=0,gate_required=account_mode && !read_ranked_policy();
    wchar_t logging[4];
    int log_enabled=GetEnvironmentVariableW(L"SZERO_LAN_MOD_LOGGING",logging,4)==1 && logging[0]==L'1';
    FILE *log=log_enabled?_wfopen(log_path,L"wb"):NULL;
    image_base=(uintptr_t)GetModuleHandleW(NULL);
    int valid=szero_native_image(image_base,0);
#ifndef SZERO_BACKEND_ADAPTER_TEST
    valid=valid && szero_bindings_init(image_base);
    for(size_t i=0;valid && i<sizeof(offsets)/sizeof(offsets[0]);++i)
        valid=szero_bind_prefix(image_base,offsets[i],prefixes[i],16);
    uintptr_t view_base=0,view_destroy=0;
    valid=valid && read_mem(image_base+szero_bind_rva(0x6d36f88),&view_base,8) &&
        view_base==image_base+szero_bind_rva(0x20f8b70) &&
        read_mem(image_base+szero_bind_rva(0x6d36f98),&view_destroy,8) && view_destroy==image_base+szero_bind_rva(0x10fddc0);
    battle_result_entry=image_base+szero_bind_rva(0x23d76a0);
    valid=valid && szero_bind_prefix(image_base,0x23d76a0,battle_result_prefix,16);
    if(!valid) goto fail;
    if(gate_required) {
        maintenance_entry=image_base+szero_bind_rva(0x5ada640);
        if(!szero_bind_prefix(image_base,0x5ada640,maintenance_prefix,16)) goto fail;
    }
    current_task=(void *(*)(void))(image_base+szero_bind_rva(offsets[5]));
    yield_cancel=(unsigned char (*)(void *))(image_base+szero_bind_rva(offsets[6]));
    native_factory=(void *(*)(uintptr_t,SzeroBackendView **))(image_base+szero_bind_rva(offsets[1]));
    native_project=(void (*)(void *,SzeroBackendRaw *))(image_base+szero_bind_rva(offsets[2]));
    native_release_stream=(void (*)(SzeroBackendOwner *))(image_base+szero_bind_rva(offsets[3]));
    native_release_headers=(void (*)(SzeroBackendHeaders *))(image_base+szero_bind_rva(offsets[4]));
    native_rank_category=(uintptr_t (*)(uintptr_t))(image_base+szero_bind_rva(offsets[7]));
    entry=image_base+szero_bind_rva(offsets[0]);
#else
    (void)offsets;(void)prefixes;(void)bytes;(void)maintenance_prefix;(void)battle_result_prefix;
    valid=valid && fixture_entry!=0;if(!valid) goto fail;
    entry=fixture_entry;
#endif
    WSADATA winsock;if(WSAStartup(MAKEWORD(2,2),&winsock)) goto fail;
    if(MH_Initialize()!=MH_OK) {WSACleanup();goto fail;}
    if(gate_required) {
        if(!maintenance_entry || MH_CreateHook((void *)maintenance_entry,(void *)&maintenance,
            (void **)&original_maintenance)!=MH_OK || MH_EnableHook((void *)maintenance_entry)!=MH_OK) {
            WSACleanup();goto fail;
        }
        memcpy(maintenance_installed,(void *)maintenance_entry,16);gate_enabled=1;
        InterlockedExchange(&ranked_allowed,read_ranked_policy());
    }
    if(!battle_result_entry || MH_CreateHook((void *)battle_result_entry,(void *)&capture_battle_result,
        (void **)&original_battle_result)!=MH_OK || MH_EnableHook((void *)battle_result_entry)!=MH_OK) {
        WSACleanup();goto fail;
    }
    memcpy(battle_result_installed,(void *)battle_result_entry,16);result_enabled=1;
    if(MH_CreateHook((void *)entry,(void *)&exchange,(void **)&original_exchange)!=MH_OK ||
        MH_EnableHook((void *)entry)!=MH_OK) {WSACleanup();goto fail;}
    memcpy(installed_prefix,(void *)entry,16);
    InterlockedExchange(&state,ARMED);
    if(log) {
        HMODULE own=NULL;char helper_hash[65]={0};
        if(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            (const wchar_t *)(uintptr_t)&worker,&own) && GetModuleFileNameW(own,path,32768))sha256(path,helper_hash);
        log_event(log,"ready");
        fprintf(log,",\"schema\":3,\"revision\":\"ranked-bindings1\",\"helper_sha256\":\"%s\","
            "\"account_mode\":%s,\"guest_ranked_gate\":%s,\"card_route\":true,\"refusal_limit\":128}\n",
            helper_hash,account_mode?"true":"false",gate_enabled?"true":"false");fflush(log);
    }
    int seen=0;unsigned logged=0,refusal_logged=0;ULONGLONG policy_checked=0;
    while(state==ARMED) {
        flush_refusals(log,&refusal_logged);
        ULONGLONG now=GetTickCount64();
        if(account_mode && now-policy_checked>=250) {
            InterlockedExchange(&ranked_allowed,read_ranked_policy());policy_checked=now;
        }
        int exists=GetFileAttributesW(endpoint)!=INVALID_FILE_ATTRIBUTES;
        if(seen && !exists) {InterlockedExchange(&state,STOPPING);break;}
        seen|=exists;
#ifdef SZERO_BACKEND_ADAPTER_TEST
        if(exists)InterlockedExchange(&fixture_endpoint_seen,1);
#endif
        if(InterlockedCompareExchange(&job.state,RUNNING,QUEUED)==QUEUED) {
            job.ok=transact();
            if(log && logged++<256) {
                log_event(log,"exchange");
                fprintf(log,",\"route\":\"%s\",\"response_received\":%s,\"size\":%llu,\"outcome\":%d,\"rank_default\":%s,\"native_category\":%d,\"native_result\":%d}\n",
                    job.path,job.ok?"true":"false",(unsigned long long)job.size,job.outcome,job.rank_default?"true":"false",job.native_category,job.native_result);fflush(log);
            }
            InterlockedExchange(&job.state,DONE);
#ifdef SZERO_BACKEND_ADAPTER_TEST
            InterlockedExchange(&fixture_done_reached,1);
            while(fixture_pause_after_done) Sleep(1);
#endif
        }
        /* Cancelled hooks leave the worker responsible for release. CAS must
         * not overwrite a new QUEUED/FILLING job after normal hook-side release. */
        if(job.hook_done) InterlockedCompareExchange(&job.state,IDLE,DONE);
        Sleep(5);
    }
    if(job.state==QUEUED) {job.ok=0;InterlockedExchange(&job.state,DONE);}
    flush_refusals(log,&refusal_logged);
    int owned=read_mem(entry,bytes,16) && !memcmp(bytes,installed_prefix,16);
    MH_STATUS restored=owned?MH_DisableHook((void *)entry):MH_ERROR_ENABLED;
    if(result_enabled) {
        owned=read_mem(battle_result_entry,bytes,16) && !memcmp(bytes,battle_result_installed,16);
        if(!owned || MH_DisableHook((void *)battle_result_entry)!=MH_OK)restored=MH_ERROR_ENABLED;
        result_enabled=0;
    }
    if(gate_enabled) {
        InterlockedExchange(&ranked_allowed,0);
        owned=read_mem(maintenance_entry,bytes,16) && !memcmp(bytes,maintenance_installed,16);
        if(!owned || MH_DisableHook((void *)maintenance_entry)!=MH_OK) restored=MH_ERROR_ENABLED;
        gate_enabled=0;
    }
    InterlockedExchange(&state,restored==MH_OK?STOPPED:FAILED);
    if(log) {fprintf(log,"{\"event\":\"stopped\",\"restored\":%s}\n",restored==MH_OK?"true":"false");fclose(log);}
    WSACleanup();return 0;
fail:
    if(result_enabled && read_mem(battle_result_entry,bytes,16) &&
       !memcmp(bytes,battle_result_installed,16))MH_DisableHook((void *)battle_result_entry);
    if(gate_enabled && read_mem(maintenance_entry,bytes,16) &&
       !memcmp(bytes,maintenance_installed,16)) MH_DisableHook((void *)maintenance_entry);
    InterlockedExchange(&state,FAILED);
    if(log) {fprintf(log,"{\"event\":\"refused\",\"binding_error\":\"%s\"}\n",szero_bindings_error());fclose(log);}
    return 0;
}
__declspec(dllexport) int szero_backend_adapter(void *lua) {
    (void)lua;DWORD error=GetLastError();wchar_t enabled[4],id[40];HMODULE own=NULL;
    if(state!=OFF || GetEnvironmentVariableW(L"SZERO_LAN_NATIVE_SESSION3",enabled,4)!=1 || enabled[0]!=L'1' ||
        GetEnvironmentVariableW(L"SZERO_LAN_INSTANCE",id,40)!=32) goto done;
    for(unsigned i=0;i<32;++i) {
        if(!((id[i]>=L'0'&&id[i]<=L'9')||(id[i]>=L'a'&&id[i]<=L'f'))) goto done;
        instance[i]=(char)id[i];
    }
    if(InterlockedCompareExchange(&state,VERIFYING,OFF)!=OFF) goto done;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
        (const wchar_t *)(uintptr_t)&szero_backend_adapter,&own) || !GetModuleFileNameW(own,endpoint,32768)) goto fail;
    wchar_t *slash=wcsrchr(endpoint,L'\\');if(!slash || slash-endpoint>32000) goto fail;
    wcscpy(log_path,endpoint);
    swprintf(log_path+(slash-endpoint)+1,200,L"native_backend_adapter_%ls.jsonl",id);
    swprintf(slash+1,200,L"lan_runtime_%ls.service.endpoint",id);
    wcscpy(account_policy,endpoint);
    wchar_t *policy_slash=wcsrchr(account_policy,L'\\');
    if(!policy_slash) goto fail;
    swprintf(policy_slash+1,200,L"lan_runtime_%ls.account.policy",id);
    account_mode=GetEnvironmentVariableW(L"SZERO_LAN_ACCOUNT_MODE",enabled,4)==1 && enabled[0]==L'1';
    game_thread=GetCurrentThreadId();
    HANDLE thread=CreateThread(NULL,0,worker,NULL,0,NULL);
    if(thread) CloseHandle(thread);else goto fail;
    goto done;
fail:InterlockedExchange(&state,FAILED);
done:SetLastError(error);return 0;
}
