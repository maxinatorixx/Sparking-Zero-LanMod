/* Resolve reviewed native operations from instruction and reference structure.
 * No executable digest, timestamp, or section-wide relocation guess is used.
 * Initialization belongs on a worker, before publishing callback pointers. */
#include "native_bindings.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#ifdef _WIN32
#include <windows.h>
#endif

typedef struct {
    uint32_t bytes,mask,length,anchor_offset,anchor_length,kind;
    int32_t result_offset;
    uint32_t displacement_offset,instruction_size,canonical;
    uint32_t literal_bytes,literal_length,literal_displacement,literal_instruction_size;
} BindingRecipe;
typedef struct {
    uint32_t canonical,old_rva,updated_rva,first,count,section_flags,prefix_length;
    unsigned char prefix[32],prefix_mask[32];
} BindingEntry;
typedef struct {
    uint32_t canonical;
    int32_t instruction_offset;
    uint32_t displacement_offset,instruction_size,target;
} BindingReference;
typedef struct {
    uint32_t canonical;
    int32_t instruction_offset;
    uint32_t displacement_offset,instruction_size,target,section_flags;
} BindingPrefixReference;
#ifndef SZERO_BINDINGS_CATALOG
#define SZERO_BINDINGS_CATALOG "native_bindings_catalog.h"
#endif
#include SZERO_BINDINGS_CATALOG
#define COUNT(a) (sizeof(a)/sizeof((a)[0]))
typedef struct {uint32_t rva,length,flags;} BindingSection;
static BindingSection sections[96];
static unsigned section_count;
static uintptr_t image_base;
static size_t image_size;
static uint32_t text_rva,text_size;
static uint32_t text_histogram[256];
static uint32_t resolved[COUNT(binding_entries)];
static char binding_error[96]="not_initialized";
#ifdef _WIN32
static volatile LONG binding_state;
#else
static int binding_state;
#endif

static int read_at(uintptr_t at,void *out,size_t size) {
#ifdef _WIN32
    SIZE_T got=0;
    return ReadProcessMemory(GetCurrentProcess(),(const void *)at,out,size,&got) && got==size;
#else
    memcpy(out,(const void *)at,size);
    return 1;
#endif
}
static uint16_t u16(const unsigned char *p) {uint16_t x;memcpy(&x,p,2);return x;}
static uint32_t u32(const unsigned char *p) {uint32_t x;memcpy(&x,p,4);return x;}
static int fail(const char *why,uint32_t canonical) {
    if(canonical)snprintf(binding_error,sizeof(binding_error),"%s_0x%x",why,canonical);
    else snprintf(binding_error,sizeof(binding_error),"%s",why);
    return 0;
}
static int readable(uintptr_t base,size_t length) {
#ifdef _WIN32
    uintptr_t end=base+length;
    if(end<base)return 0;
    while(base<end) {
        MEMORY_BASIC_INFORMATION m;
        if(!VirtualQuery((const void *)base,&m,sizeof(m)) || m.State!=MEM_COMMIT ||
           m.AllocationBase!=(void *)image_base || (m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return 0;
        uintptr_t next=(uintptr_t)m.BaseAddress+m.RegionSize;
        if(next<=base)return 0;
        base=next;
    }
#else
    (void)base;(void)length;
#endif
    return 1;
}
static int parse_image(uintptr_t base,size_t accessible) {
    unsigned char dos[64],nt[264],sh[40];
    if(!base || accessible<sizeof(dos) || !read_at(base,dos,sizeof(dos)) || u16(dos)!=0x5a4d)return fail("invalid_pe64",0);
    uint32_t off=u32(dos+60);
    if(off<64 || off>1024*1024 || off>accessible || accessible-off<sizeof(nt) || base>UINTPTR_MAX-off ||
       !read_at(base+off,nt,sizeof(nt)) || u32(nt)!=0x4550 || u16(nt+4)!=0x8664 || u16(nt+24)!=0x20b)return fail("invalid_pe64",0);
    unsigned count=u16(nt+6),optional=u16(nt+20);
    uint32_t length=u32(nt+24+56),headers=u32(nt+24+60);
    size_t table=(size_t)off+24+optional;
    if(!count || count>COUNT(sections) || optional<240 || length<headers || length>0x7fffffff ||
       length>accessible || headers>1024*1024 || table>headers || count>(headers-table)/40 || base>UINTPTR_MAX-length)
        return fail("invalid_pe64_bounds",0);
    image_base=base;image_size=length;section_count=count;text_rva=0;text_size=0;
    for(unsigned i=0;i<count;i++) {
        if(!read_at(base+table+(size_t)i*40,sh,sizeof(sh)))return fail("unreadable_sections",0);
        uint32_t rva=u32(sh+12),size=u32(sh+8),flags=u32(sh+36);
        if(!size || rva<headers || rva>length || size>length-rva)return fail("invalid_section_bounds",0);
        sections[i]=(BindingSection){rva,size,flags};
        if(!memcmp(sh,".text\0\0\0",8)) {
            if(text_rva || !(flags&0x20000000) || !(flags&0x40000000))return fail("invalid_text_section",0);
            text_rva=rva;text_size=size;
        }
        if(!memcmp(sh,".text\0\0\0",8) && !readable(base+rva,size))return fail("unreadable_text_section",0);
    }
    return text_rva && text_size ? 1 : fail("missing_text_section",0);
}
static int target_section(uint32_t rva,uint32_t flags) {
    size_t size=(flags&0x20000000)?1:8;
    for(unsigned i=0;i<section_count;i++) {
        const BindingSection *s=&sections[i];
        if(rva>=s->rva && rva-s->rva<=s->length && size<=s->length-(rva-s->rva) &&
           (s->flags&0x40000000) && (s->flags&(0x20000000u|0x80000000u))==flags && readable(image_base+rva,size))return 1;
    }
    return 0;
}
static int recipe_matches(const BindingRecipe *r,const unsigned char *at) {
    const unsigned char *data=binding_bytes+r->bytes,*mask=binding_bytes+r->mask;
    for(uint32_t i=0;i<r->length;i++)if(mask[i] && at[i]!=data[i])return 0;
    return 1;
}
static int resolve_recipe(const BindingRecipe *r,uint32_t *result) {
    if(!r->anchor_length || r->anchor_offset>r->length || r->anchor_length>r->length-r->anchor_offset || r->length>text_size)
        return fail("invalid_catalog",r->canonical);
    const unsigned char *text=(const unsigned char *)(image_base+text_rva),*data=binding_bytes+r->bytes;
    const unsigned char *needle=data+r->anchor_offset;
    /* Scan on the least frequent fixed anchor byte. x64 0x48/0x00 and padding
     * are common; using the first byte would multiply candidate comparisons.
     * This only reduces work: every matching candidate and ambiguity remains
     * checked against the complete normalized instruction pattern. */
    uint32_t pivot=0;
    for(uint32_t i=1;i<r->anchor_length;i++)
        if(text_histogram[needle[i]]<text_histogram[needle[pivot]])pivot=i;
    size_t needle_offset=(size_t)r->anchor_offset+pivot;
    size_t position=needle_offset,count=0;
    size_t last=text_size-r->length+needle_offset;
    uint32_t found=0;
    while(position<=last) {
        const unsigned char *at=memchr(text+position,needle[pivot],last-position+1);
        if(!at)break;
        size_t hit=(size_t)(at-text);
        position=hit+1;
        size_t start=hit-needle_offset;
        if(memcmp(text+start+r->anchor_offset,needle,r->anchor_length) || !recipe_matches(r,text+start))continue;
        if(r->literal_length) {
            if(r->literal_displacement+4>r->length)return fail("invalid_catalog_literal",r->canonical);
            int32_t displacement;
            memcpy(&displacement,text+start+r->literal_displacement,4);
            int64_t literal=(int64_t)text_rva+(int64_t)start+r->literal_instruction_size+displacement;
            if(literal<0 || (uint64_t)literal>image_size || r->literal_length>image_size-(size_t)literal ||
               !readable(image_base+(uintptr_t)literal,r->literal_length) ||
               memcmp((const void *)(image_base+(uintptr_t)literal),binding_bytes+r->literal_bytes,r->literal_length))continue;
        }
        if(++count>1)return fail("ambiguous_binding",r->canonical);
        int64_t value=(int64_t)text_rva+(int64_t)start+r->result_offset;
        if(r->kind==1) {
            if(r->displacement_offset+4>r->length)return fail("invalid_catalog_reference",r->canonical);
            int32_t disp;
            memcpy(&disp,text+start+r->displacement_offset,4);
            value+=(int64_t)r->instruction_size+disp;
        } else if(r->kind!=0)return fail("invalid_catalog_kind",r->canonical);
        if(value<=0 || (uint64_t)value>=image_size)return fail("reference_out_of_bounds",r->canonical);
        found=(uint32_t)value;
    }
    if(!count)return fail("missing_binding",r->canonical);
    *result=found;
    return 1;
}
static size_t entry_index(uintptr_t canonical) {
    size_t lo=0,hi=COUNT(binding_entries);
    while(lo<hi) {size_t mid=lo+(hi-lo)/2;if(binding_entries[mid].canonical<canonical)lo=mid+1;else hi=mid;}
    return lo<COUNT(binding_entries) && binding_entries[lo].canonical==canonical?lo:COUNT(binding_entries);
}
static int initialize(uintptr_t base,size_t accessible) {
    if(!parse_image(base,accessible))return 0;
    memset(text_histogram,0,sizeof(text_histogram));
    const unsigned char *text=(const unsigned char *)(image_base+text_rva);
    for(uint32_t i=0;i<text_size;i++)text_histogram[text[i]]++;
    for(size_t i=0;i<COUNT(binding_entries);i++) {
        const BindingEntry *e=&binding_entries[i];
        uint32_t value=0;
        if(!e->count || e->first>COUNT(binding_recipes) || e->count>COUNT(binding_recipes)-e->first)return fail("invalid_catalog",e->canonical);
        for(uint32_t j=0;j<e->count;j++) {
            uint32_t next=0;
            if(!resolve_recipe(&binding_recipes[e->first+j],&next))return 0;
            if(j && value!=next)return fail("conflicting_references",e->canonical);
            value=next;
        }
        if(!target_section(value,e->section_flags))return fail("wrong_binding_section",e->canonical);
        resolved[i]=value;
    }
    for(size_t i=0;i<COUNT(binding_references);i++) {
        const BindingReference *r=&binding_references[i];
        size_t from=entry_index(r->canonical),to=entry_index(r->target);
        if(from==COUNT(binding_entries) || to==COUNT(binding_entries))return fail("invalid_catalog_reference",r->canonical);
        int64_t at=(int64_t)resolved[from]+r->instruction_offset;
        if(at<text_rva || at+(int64_t)r->instruction_size>(int64_t)text_rva+text_size || r->displacement_offset+4>r->instruction_size)
            return fail("reference_out_of_bounds",r->canonical);
        int32_t disp;
        memcpy(&disp,(const void *)(image_base+(uintptr_t)at+r->displacement_offset),4);
        if(at+r->instruction_size+disp!=resolved[to])return fail("binding_reference_mismatch",r->canonical);
    }
    snprintf(binding_error,sizeof(binding_error),"ready_native_layout");
    return 1;
}
int szero_bindings_init(uintptr_t base) {
#ifdef _WIN32
    LONG prior=InterlockedCompareExchange(&binding_state,1,0);
#else
    int prior=binding_state;if(!prior)binding_state=1;
#endif
    if(prior)return prior==2 && base==image_base;
    int ok=initialize(base,SIZE_MAX);
#ifdef _WIN32
    InterlockedExchange(&binding_state,ok?2:3);
#else
    binding_state=ok?2:3;
#endif
    return ok;
}
#ifdef SZERO_BINDINGS_PORTABLE_TEST
int szero_bindings_init_image(uintptr_t base,size_t accessible) {
    if(binding_state)return binding_state==2 && base==image_base;
    binding_state=1;
    int ok=initialize(base,accessible);
    binding_state=ok?2:3;
    return ok;
}
#endif
uintptr_t szero_bind_rva(uintptr_t canonical) {
    if(binding_state!=2)return 0;
    if(canonical==0x8cf8500u) {size_t at=entry_index(0x8cf84f8u);return at<COUNT(binding_entries)?resolved[at]+8u:0;}
    size_t at=entry_index(canonical);
    return at<COUNT(binding_entries)?resolved[at]:0;
}
const char *szero_bindings_error(void) {return binding_error;}
int szero_bind_prefix(uintptr_t base,uintptr_t canonical,const unsigned char *prefix,size_t length) {
    if(binding_state!=2 || base!=image_base || !prefix || !length)return 0;
    size_t i=entry_index(canonical);
    if(i==COUNT(binding_entries))return 0;
    const BindingEntry *e=&binding_entries[i];
    if(length>e->prefix_length || resolved[i]>image_size || length>image_size-resolved[i] || memcmp(prefix,e->prefix,length))return 0;
    const unsigned char *actual=(const unsigned char *)(base+resolved[i]);
    for(size_t j=0;j<length;j++)if(e->prefix_mask[j] && actual[j]!=prefix[j])return 0;
    for(size_t j=0;j<COUNT(binding_prefix_references);j++) {
        const BindingPrefixReference *r=&binding_prefix_references[j];
        if(r->canonical!=canonical || r->instruction_offset<0 ||
           (uint64_t)r->instruction_offset+r->instruction_size>length)continue;
        if(r->displacement_offset+4>r->instruction_size)return 0;
        int32_t displacement;
        memcpy(&displacement,actual+r->instruction_offset+r->displacement_offset,4);
        int64_t target=(int64_t)resolved[i]+r->instruction_offset+r->instruction_size+displacement;
        if(target<=0 || (uint64_t)target>=image_size || !target_section((uint32_t)target,r->section_flags))return 0;
        if(r->target) {
            size_t to=entry_index(r->target);
            if(to==COUNT(binding_entries) || target!=resolved[to])return 0;
        }
    }
    return 1;
}
