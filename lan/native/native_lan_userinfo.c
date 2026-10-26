#include "native_lan_userinfo.h"
#include "native_lan_identity.h"
#include <stdlib.h>
#include <string.h>
_Static_assert(sizeof(SzeroNativeString)==32,"Native ID ABI");
_Static_assert(sizeof(SzeroUserInfoVector)==24,"Native vector ABI");
_Static_assert(sizeof(SzeroUserInfoRecord)==40,"Native relationship ABI");
static int read_range(const SzeroUserInfoCallbacks *cb,uintptr_t p,void *out,size_t n) {
    return p && n<=UINTPTR_MAX-p && cb->read(cb->context,p,out,n);
}
/* 0=real namespace;1=canonical LAN;-1=malformed/unreadable. Read only6B of a
 * real platform ID, never parse/coerce it as a number or change its bytes. */
static int classify(const SzeroNativeString *id,const SzeroUserInfoCallbacks *cb,
    unsigned char principal[38]) {
    const unsigned char *raw=(const unsigned char *)id;
    uint64_t n;uintptr_t p;
    if(id->words[0]&1) {
        n=id->words[2];p=(uintptr_t)id->words[1];
        if(n>id->words[3]) return -1;
    } else {n=raw[0]>>2;p=(uintptr_t)(raw+1);if(n>30) return -1;}
    if(n<6) return 0;
    unsigned char prefix[6];
    if(id->words[0]&1) {if(!read_range(cb,p,prefix,6)) return -1;}
    else memcpy(prefix,raw+1,6);
    if(memcmp(prefix,"szlan:",6)) return 0;
    if(n!=38 || !read_range(cb,p,principal,38) ||
       !szero_lan_identity_valid(principal,38)) return -1;
    return 1;
}
int szero_lan_userinfo_dispatch(void *self,void *out,const void *ids,void *records,
    const SzeroUserInfoCallbacks *cb) {
    if(!cb || !cb->read || !cb->writable || !cb->write || !cb->ready ||
       !cb->known || !cb->original) return SZERO_USERINFO_REFUSED;
    SzeroUserInfoVector input;
    if(!read_range(cb,(uintptr_t)ids,&input,sizeof(input)) ||
       input.count>input.capacity || input.count>SZERO_USERINFO_MAX_IDS ||
       (input.count && (!input.data || input.count>(UINTPTR_MAX-input.data)/32)))
        return SZERO_USERINFO_REFUSED;
    SzeroNativeString *real=calloc(input.count?input.count:1,sizeof(*real));
    unsigned char *lan=calloc(input.count?input.count:1,38);
    if(!real || !lan) {free(real);free(lan);return SZERO_USERINFO_REFUSED;}
    size_t real_count=0,lan_count=0;
    int result=SZERO_USERINFO_REFUSED;
    for(size_t i=0;i<input.count;i++) {
        SzeroNativeString value;unsigned char principal[38];
        if(!read_range(cb,input.data+i*32,&value,sizeof(value))) goto done;
        int kind=classify(&value,cb,principal);
        if(kind<0) goto done;
        if(!kind) {real[real_count++]=value;continue;}
        if(!cb->ready(cb->context) || !cb->known(cb->context,principal)) goto done;
        for(size_t j=0;j<lan_count;j++) if(!memcmp(lan+j*38,principal,38)) goto done;
        memcpy(lan+lan_count++*38,principal,38);
    }
    if(!lan_count) {
        cb->original(cb->context,self,out,ids,records);
        result=SZERO_USERINFO_DELEGATED;goto done;
    }
    /* Caller constructed missing-ID records before invoking user+98. Validate
     * those native-owned records; do not synthesize native allocation/layout. */
    SzeroUserInfoVector rows;
    if(!read_range(cb,(uintptr_t)records,&rows,sizeof(rows)) ||
       rows.count>rows.capacity || rows.count>SZERO_USERINFO_MAX_IDS ||
       (rows.count && (!rows.data || rows.count>(UINTPTR_MAX-rows.data)/40)) ||
       !cb->writable(cb->context,(uintptr_t)out,48) ||
       !cb->writable(cb->context,(uintptr_t)records,sizeof(rows))) goto done;
    unsigned char *found=calloc(lan_count,1);
    uintptr_t *flags=calloc(rows.count?rows.count:1,sizeof(*flags));
    if(!found || !flags) {free(found);free(flags);goto done;}
    size_t flag_count=0;
    for(size_t i=0;i<rows.count;i++) {
        SzeroUserInfoRecord row;unsigned char principal[38];
        if(!read_range(cb,rows.data+i*40,&row,sizeof(row))) goto rows_done;
        int kind=classify(&row.id,cb,principal);
        if(kind<0) goto rows_done;
        if(!kind) continue;
        if(!cb->known(cb->context,principal) ||
           !cb->writable(cb->context,rows.data+i*40+32,1)) goto rows_done;
        int requested=0;
        for(size_t j=0;j<lan_count;j++) if(!memcmp(lan+j*38,principal,38)) {
            if(found[j]) goto rows_done;
            found[j]=1;requested=1;
        }
        if(requested) flags[flag_count++]=rows.data+i*40+32;
    }
    for(size_t j=0;j<lan_count;j++) if(!found[j]) goto rows_done;
    /* Original1458d4a00 may MOVE invalid real strings into native records,
     * then1458c0760 destroys removed strings and compacts the ID array. A
     * shallow ownership copy would double-free the caller's source strings.
     * The array itself is borrowed (original erase does not free/reallocate
     * it); only its independently-native-owned string elements may transfer. */
    SzeroNativeString *copies=NULL;
    if(real_count) {
        if(!cb->copy_id || !cb->destroy_id) goto rows_done;
        copies=calloc(real_count,sizeof(*copies));
        if(!copies) goto rows_done;
        size_t copied=0;
        for(;copied<real_count;copied++) if(!cb->copy_id(cb->context,copies+copied,real+copied)) break;
        if(copied!=real_count) {
            for(size_t j=0;j<copied;j++) cb->destroy_id(cb->context,copies+j);
            free(copies);goto rows_done;
        }
    }
    /* LAN relationship byte0 means no local LAN restrictions. These are LAN
     * principals admitted by our own directory, not forged Steam accounts.
     * Actual account/platform methods and real-ID results remain untouched. */
    for(size_t i=0;i<flag_count;i++) {
        const unsigned char neutral=0;cb->write(cb->context,flags[i],&neutral,1);
    }
    if(real_count) {
        uint64_t filtered[4]={(uintptr_t)copies,real_count,real_count,0};
        cb->original(cb->context,self,out,filtered,records);
        /* Exact original1458c0760 only reduces count, destroys removed
         * elements, and retains the array/capacity. Remaining IDs still ours. */
        if(filtered[0]==(uintptr_t)copies && filtered[1]<=real_count)
            for(size_t j=0;j<filtered[1];j++) cb->destroy_id(cb->context,copies+j);
        free(copies);
        result=SZERO_USERINFO_DELEGATED;
    } else {
        unsigned char output[48]={0};uint32_t tag=2;
        memcpy(output,&tag,4);memcpy(output+8,&rows,sizeof(rows));
        const SzeroUserInfoVector empty={0};
        cb->write(cb->context,(uintptr_t)records,&empty,sizeof(empty));
        cb->write(cb->context,(uintptr_t)out,output,sizeof(output));
        result=SZERO_USERINFO_LAN;
    }
rows_done:
    free(found);free(flags);
done:
    /* Only our borrowed snapshots, never any native strings/vector storage. */
    free(real);free(lan);return result;
}
