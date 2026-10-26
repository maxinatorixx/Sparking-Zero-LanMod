#include "native_session_inspect.h"
#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned char query[0x50], settings[0x40], text[256];
    int32_t numeric[SZERO_WIRE_MAX_NUMERIC];
    size_t text_size;
} Scratch;
static uint64_t word(const void *p) {uint64_t n;memcpy(&n,p,8);return n;}
static uint32_t dword(const void *p) {uint32_t n;memcpy(&n,p,4);return n;}
static int range(SzeroWireRead read,void *user,uintptr_t p,void *out,size_t n) {
    return p && n<=UINTPTR_MAX-p && read(p,out,n,user);
}
static int text_at(Scratch *s,uintptr_t p,SzeroWireRead read,void *user) {
    unsigned char header[32];
    if(!range(read,user,p,header,sizeof(header))) return 0;
    size_t n;
    if(header[0]&1) {
        uint64_t length=word(header+16);
        if(length>SZERO_WIRE_MAX_TEXT || length>word(header+24)) return 0;
        n=(size_t)length;
        if(n && !range(read,user,(uintptr_t)word(header+8),s->text,n)) return 0;
    } else {
        n=header[0]>>2;
        if(n>30) return 0;
        if(n) memcpy(s->text,header+1,n);
    }
    if(n && memchr(s->text,0,n)) return 0;
    s->text[n]=0;s->text_size=n;return 1;
}
static int equal(const Scratch *s,SzeroText text) {
    return text.size==s->text_size && (!text.size ||
        (text.data && !memcmp(text.data,s->text,text.size)));
}
static int predicate(const unsigned char *raw,const Scratch *s,size_t count) {
    uint64_t key=word(raw);int32_t comparison,value;
    memcpy(&comparison,raw+8,4);memcpy(&value,raw+12,4);
    if(comparison<0 || comparison>4) return -1;
    if(key>=count) return 1; /* Original missing positional key is permissive. */
    int32_t actual=s->numeric[key];
    switch(comparison) {
      case 0:return actual==value;case 1:return actual<value;
      case 2:return actual<=value;case 3:return actual>value;
      default:return actual>=value;
    }
}
static int filters(Scratch *s,uintptr_t p,size_t count,size_t stride,
    size_t numeric_count,SzeroWireRead read,void *user,int *pass) {
    unsigned char raw[32];
    if(count && (!p || count> (UINTPTR_MAX-p)/stride)) return 0;
    for(size_t i=0;i<count;i++) {
        if(!range(read,user,p+i*stride,raw,stride)) return 0;
        int first=predicate(raw,s,numeric_count),second=0;
        if(stride==32) second=predicate(raw+16,s,numeric_count);
        if(first<0 || second<0) return 0;
        if(!first && !second) *pass=0;
    }
    return 1;
}
static int inspect(Scratch *s,uintptr_t descriptor,uintptr_t query,
    const SzeroSessionData *expected,const SzeroTextWire *local,int normalize,
    SzeroWireRead read,void *user,SzeroSessionInspection *out) {
    if(descriptor>UINTPTR_MAX-0xe8 || !expected || !expected->members ||
       expected->member_count<1 || !expected->capacity ||
       expected->capacity>SZERO_MATERIALIZER_MAX_MEMBERS || expected->member_count>expected->capacity ||
       expected->numeric_count>SZERO_WIRE_MAX_NUMERIC ||
       (expected->numeric_count && !expected->numeric) ||
       expected->id.size>SZERO_WIRE_MAX_TEXT ||
       (expected->id.size && !expected->id.data)) return 0;
    size_t owner=SIZE_MAX;
    for(size_t i=0;i<expected->member_count;i++) if(expected->members[i].owner) {
        if(owner!=SIZE_MAX) return 0;
        owner=i;
    }
    if(owner==SIZE_MAX) return 0;
    SzeroText owner_text=expected->members[owner].identity[0];
    if(owner_text.size>SZERO_WIRE_MAX_TEXT || (owner_text.size && !owner_text.data)) return 0;
    if(!range(read,user,descriptor+0x48,s->settings,sizeof(s->settings))) return 0;
    uint64_t count=word(s->settings+0x10);
    if(count>SZERO_WIRE_MAX_NUMERIC || count>word(s->settings+0x18)) return 0;
    if(count && !range(read,user,(uintptr_t)word(s->settings+8),s->numeric,(size_t)count*4)) return 0;
    int mask=0;
    if(dword(s->settings)!=expected->compatibility) mask|=SZERO_INSPECT_COMPATIBILITY;
    if(count!=expected->numeric_count) mask|=SZERO_INSPECT_NUMERIC_COUNT;
    size_t common=count<expected->numeric_count?(size_t)count:expected->numeric_count;
    if(common && memcmp(s->numeric,expected->numeric,common*4)) mask|=SZERO_INSPECT_NUMERIC_VALUES;
    if(s->settings[0x38]!=expected->capacity) mask|=SZERO_INSPECT_CAPACITY;
    unsigned char members=0;
    if(!range(read,user,descriptor+0xe0,&members,1)) return 0;
    if(members!=expected->member_count) mask|=SZERO_INSPECT_MEMBER_COUNT;
    if(!text_at(s,descriptor,read,user)) return 0;
    if(!equal(s,expected->id)) mask|=SZERO_INSPECT_ID;
    if(!text_at(s,descriptor+0x88,read,user)) return 0;
    if(!equal(s,owner_text)) mask|=SZERO_INSPECT_OWNER_PRIMARY;
    if(local) {
        if(local->size>SZERO_WIRE_MAX_TEXT ||
           (local->size && memchr(local->bytes,0,(size_t)local->size))) return 0;
        out->owner_equal=equal(s,(SzeroText){local->bytes,(size_t)local->size});
    }
    out->copy_mask=mask;
    if(!query) return 1;
    if(!range(read,user,query,s->query,sizeof(s->query))) return 0;
    uint64_t n=word(s->query+0x10),pairs=word(s->query+0x30);
    if(n>16 || n>word(s->query+0x18) || pairs>16 || pairs>word(s->query+0x38)) return 0;
    int pass=1;
    uint32_t a=dword(s->query),b=dword(s->settings);
    int mode=s->query[0x4e]==255?normalize:s->query[0x4e]!=0;
    if(mode<0 || mode>1) return 0;
    if(a && b) {
        if(mode) {a=(a-1)%1000;b=(b-1)%1000;}
        if(a!=b) pass=0;
    }
    if(!filters(s,(uintptr_t)word(s->query+8),(size_t)n,16,(size_t)count,read,user,&pass) ||
       !filters(s,(uintptr_t)word(s->query+0x28),(size_t)pairs,32,(size_t)count,read,user,&pass)) return 0;
    out->numeric_pass=pass;
    /* Original outer wrapper skips this filter for an empty local primary. */
    out->self_exclusion=s->query[0x4d] ?
        (local && !local->size ? 0 : out->owner_equal) : 0;
    return 1;
}
void szero_native_session_inspect(uintptr_t descriptor,uintptr_t query,
    const SzeroSessionData *expected,const SzeroTextWire *local_primary,
    int default_normalize,SzeroWireRead read,void *user,SzeroSessionInspection *out) {
    if(!out) return;
    *out=(SzeroSessionInspection){0,-1,-1,-1,-1};
    if(!read) return;
    Scratch *scratch=calloc(1,sizeof(*scratch));
    if(!scratch) return;
    out->read_ok=inspect(scratch,descriptor,query,expected,local_primary,
        default_normalize,read,user,out);
    free(scratch);
}
