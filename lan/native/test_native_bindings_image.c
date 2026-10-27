/* Read-only artifact comparison: map PE bytes as DATA, never run game code. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native_bindings.h"
/* Catalog access is confined to fault injection. Assertions are against the
 * resolver's public API; no mapped game instruction is ever called. */
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
#include "native_bindings_catalog.h"
#define COUNT(a) (sizeof(a)/sizeof((a)[0]))
static const uint32_t hooked_entries[]={
    0x5a9c800,0x23d76a0,0x5ada640,0x5a7e7c0,0x58b1e90,0x5ad9740,
    0x58f19f0,0x5ad9b00,0x5ad0d20,0x591cb70,0x5851440,0x5811d40,
    0x59aecb0,0x59bd290,0x59c9fd0,0x5985340,0x59acbf0,0x5993410,0x59b86c0
};
static const BindingEntry *catalog_entry(uint32_t canonical) {
    for(size_t i=0;i<COUNT(binding_entries);i++)
        if(binding_entries[i].canonical==canonical)return &binding_entries[i];
    assert(!"missing fixture catalog entry");return NULL;
}
static int prefix_matches(const unsigned char *mapped,uint32_t rva,const BindingEntry *e) {
    assert(e->prefix_length>=16);
    for(unsigned i=0;i<16;i++)
        if(e->prefix_mask[i] && mapped[rva+i]!=e->prefix[i])return 0;
    return 1;
}
static unsigned select_fixture_layout(const unsigned char *mapped,uint32_t shift) {
    /* Hints are used only to place synthetic damage, never by the resolver.
     * All reviewed hook prefixes must agree on one placement. */
    unsigned scores[2]={0};
    for(unsigned layout=0;layout<2;layout++)
        for(size_t i=0;i<COUNT(hooked_entries);i++) {
            const BindingEntry *e=catalog_entry(hooked_entries[i]);
            uint32_t rva=(layout?e->updated_rva:e->old_rva)+shift;
            scores[layout]+=(unsigned)prefix_matches(mapped,rva,e);
        }
    assert((scores[0]==COUNT(hooked_entries))!=(scores[1]==COUNT(hooked_entries)));
    return scores[1]==COUNT(hooked_entries);
}
static void corrupt_active_anchor(unsigned char *mapped,const IMAGE_NT_HEADERS64 *nt) {
    const BindingRecipe *r=&binding_recipes[binding_entries[0].first];
    const IMAGE_SECTION_HEADER *sections=IMAGE_FIRST_SECTION(nt);
    const IMAGE_SECTION_HEADER *text=NULL;
    for(unsigned i=0;i<nt->FileHeader.NumberOfSections;i++)
        if(!memcmp(sections[i].Name,".text\0\0\0",8))text=&sections[i];
    assert(text && r->length && r->anchor_length && r->length<=text->Misc.VirtualSize);
    unsigned changed=0;
    unsigned char *code=mapped+text->VirtualAddress;
    for(size_t at=0;at<=text->Misc.VirtualSize-r->length;at++) {
        if(memcmp(code+at+r->anchor_offset,binding_bytes+r->bytes+r->anchor_offset,r->anchor_length))continue;
        size_t j=0;
        for(;j<r->length;j++)
            if(binding_bytes[r->mask+j] && code[at+j]!=binding_bytes[r->bytes+j])break;
        if(j!=r->length)continue;
        assert(binding_bytes[r->mask+r->anchor_offset]);
        code[at+r->anchor_offset]^=1;
        changed++;
    }
    assert(changed==1);
    printf("corrupted_anchor=0x%x matches=%u\n",r->canonical,changed);
}

int wmain(int argc,wchar_t **argv) {
    assert(argc>=2 && argc<=5);
    uint32_t shift=0;
    int hooked=0,corrupt=0;
    for(int i=2;i<argc;i++) {
        if(!wcscmp(argv[i],L"--shift"))shift=0x2000;
        else if(!wcscmp(argv[i],L"--hooked"))hooked=1;
        else if(!wcscmp(argv[i],L"--corrupt"))corrupt=1;
        else assert(!"unknown fixture mode");
    }
    (void)binding_references;
    (void)binding_prefix_references;
    FILE *file=_wfopen(argv[1],L"rb");
    assert(file);
    assert(!fseek(file,0,SEEK_END));
    long length=ftell(file);
    assert(length>0 && !fseek(file,0,SEEK_SET));
    unsigned char *disk=malloc((size_t)length);
    assert(disk && fread(disk,1,(size_t)length,file)==(size_t)length);
    fclose(file);
    IMAGE_DOS_HEADER *dos=(IMAGE_DOS_HEADER *)disk;
    assert(dos->e_magic==IMAGE_DOS_SIGNATURE && dos->e_lfanew>0);
    assert((size_t)dos->e_lfanew+sizeof(IMAGE_NT_HEADERS64)<(size_t)length);
    IMAGE_NT_HEADERS64 *nt=(IMAGE_NT_HEADERS64 *)(disk+dos->e_lfanew);
    assert(nt->Signature==IMAGE_NT_SIGNATURE && nt->OptionalHeader.Magic==IMAGE_NT_OPTIONAL_HDR64_MAGIC);
    unsigned char *mapped=VirtualAlloc(NULL,(size_t)nt->OptionalHeader.SizeOfImage+shift,
                                      MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    assert(mapped && nt->OptionalHeader.SizeOfHeaders<=(size_t)length);
    memcpy(mapped,disk,nt->OptionalHeader.SizeOfHeaders);
    IMAGE_SECTION_HEADER *sections=IMAGE_FIRST_SECTION(nt);
    for(unsigned i=0;i<nt->FileHeader.NumberOfSections;i++) {
        assert((uint64_t)sections[i].PointerToRawData+sections[i].SizeOfRawData<=(uint64_t)length);
        assert((uint64_t)sections[i].VirtualAddress+sections[i].SizeOfRawData<=nt->OptionalHeader.SizeOfImage);
        memcpy(mapped+sections[i].VirtualAddress+shift,disk+sections[i].PointerToRawData,sections[i].SizeOfRawData);
    }
    IMAGE_DATA_DIRECTORY relocation=nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_BASERELOC];
    assert((uint64_t)relocation.VirtualAddress+relocation.Size<=nt->OptionalHeader.SizeOfImage);
    size_t offset=0;
    intptr_t delta=(intptr_t)(uintptr_t)mapped-(intptr_t)nt->OptionalHeader.ImageBase+shift;
    while(offset<relocation.Size) {
        IMAGE_BASE_RELOCATION *block=(IMAGE_BASE_RELOCATION *)(mapped+relocation.VirtualAddress+shift+offset);
        assert(block->SizeOfBlock>=sizeof(*block) && block->SizeOfBlock<=relocation.Size-offset);
        WORD *entries=(WORD *)(block+1);
        for(unsigned i=0;i<(block->SizeOfBlock-sizeof(*block))/sizeof(WORD);i++) {
            unsigned type=entries[i]>>12,within=entries[i]&0xfff;
            if(type==IMAGE_REL_BASED_ABSOLUTE)continue;
            assert(type==IMAGE_REL_BASED_DIR64);
            size_t target=(size_t)block->VirtualAddress+within;
            assert(target<=nt->OptionalHeader.SizeOfImage-sizeof(uint64_t));
            uint64_t value;
            memcpy(&value,mapped+target+shift,sizeof(value));
            value+=(uint64_t)delta;
            memcpy(mapped+target+shift,&value,sizeof(value));
        }
        block->VirtualAddress+=shift;
        offset+=block->SizeOfBlock;
    }
    IMAGE_NT_HEADERS64 *mapped_nt=(IMAGE_NT_HEADERS64 *)(mapped+dos->e_lfanew);
    IMAGE_SECTION_HEADER *mapped_sections=IMAGE_FIRST_SECTION(mapped_nt);
    if(shift) {
        mapped_nt->OptionalHeader.SizeOfImage+=shift;
        mapped_nt->OptionalHeader.AddressOfEntryPoint+=shift;
        mapped_nt->OptionalHeader.BaseOfCode+=shift;
        for(unsigned i=0;i<mapped_nt->FileHeader.NumberOfSections;i++)
            mapped_sections[i].VirtualAddress+=shift;
        for(unsigned i=0;i<IMAGE_NUMBEROF_DIRECTORY_ENTRIES;i++)
            if(i!=IMAGE_DIRECTORY_ENTRY_SECURITY && mapped_nt->OptionalHeader.DataDirectory[i].VirtualAddress)
                mapped_nt->OptionalHeader.DataDirectory[i].VirtualAddress+=shift;
        IMAGE_DATA_DIRECTORY exceptions=mapped_nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION];
        assert((uint64_t)exceptions.VirtualAddress+exceptions.Size<=mapped_nt->OptionalHeader.SizeOfImage);
        RUNTIME_FUNCTION *functions=(RUNTIME_FUNCTION *)(mapped+exceptions.VirtualAddress);
        for(size_t i=0;i<exceptions.Size/sizeof(*functions);i++) {
            if(functions[i].BeginAddress)functions[i].BeginAddress+=shift;
            if(functions[i].EndAddress)functions[i].EndAddress+=shift;
            if(functions[i].UnwindData)functions[i].UnwindData+=shift;
        }
    }
    unsigned layout=hooked?select_fixture_layout(mapped,shift):0;
    if(hooked) {
        for(size_t i=0;i<COUNT(hooked_entries);i++) {
            const BindingEntry *e=catalog_entry(hooked_entries[i]);
            memset(mapped+(layout?e->updated_rva:e->old_rva)+shift,0xcc,16);
        }
        printf("hooked_entries=%llu\n",(unsigned long long)COUNT(hooked_entries));
    }
    if(corrupt)corrupt_active_anchor(mapped,mapped_nt);
    free(disk);
    LARGE_INTEGER frequency,started,finished;
    assert(QueryPerformanceFrequency(&frequency) && QueryPerformanceCounter(&started));
    int ok=szero_bindings_init((uintptr_t)mapped);
    assert(QueryPerformanceCounter(&finished));
    printf("resolver_ms=%.3f\n",1000.0*(double)(finished.QuadPart-started.QuadPart)/(double)frequency.QuadPart);
    printf("resolve=%d error=%s\n",ok,szero_bindings_error());
    if(corrupt) {
        assert(!ok);
        assert(VirtualFree(mapped,0,MEM_RELEASE));
        puts("corrupt native signature refused without executing game code");
        return 0;
    }
    if(!ok)return 1;
    if(!hooked) {
        unsigned checked=0;
        for(size_t i=0;i<COUNT(binding_entries);i++) {
            const BindingEntry *e=&binding_entries[i];
            if(e->prefix_length<16)continue;
            if(!szero_bind_prefix((uintptr_t)mapped,e->canonical,e->prefix,16)) {
                printf("unexpected_prefix_refusal=0x%x\n",e->canonical);
                return 1;
            }
            checked++;
        }
        printf("prefixes_validated=%u\n",checked);
    }
    if(hooked) {
        for(size_t i=0;i<COUNT(hooked_entries);i++) {
            const BindingEntry *e=catalog_entry(hooked_entries[i]);
            assert(szero_bind_rva(e->canonical)==(layout?e->updated_rva:e->old_rva)+shift);
            assert(!szero_bind_prefix((uintptr_t)mapped,e->canonical,e->prefix,16));
        }
        printf("hooked_prefixes_rejected=%llu\n",(unsigned long long)COUNT(hooked_entries));
    }
    printf("context=%llx result=%llx service=%llx shift=%x\n",
        (unsigned long long)szero_bind_rva(0x8cf84f8),
        (unsigned long long)szero_bind_rva(0x23d76a0),
        (unsigned long long)szero_bind_rva(0x7b95320),shift);
    assert(VirtualFree(mapped,0,MEM_RELEASE));
    puts("artifact bindings resolved without executing game code");
    return 0;
}
