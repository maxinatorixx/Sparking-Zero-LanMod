#define WIN32_LEAN_AND_MEAN
#include "native_image.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    assert(szero_native_image((uintptr_t)GetModuleHandleW(NULL),0));
    unsigned char *memory=VirtualAlloc(NULL,0x4000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    assert(memory);
    IMAGE_DOS_HEADER *dos=(void *)memory;
    IMAGE_NT_HEADERS64 *nt=(void *)(memory+0x100);
    dos->e_magic=IMAGE_DOS_SIGNATURE;dos->e_lfanew=0x100;
    nt->Signature=IMAGE_NT_SIGNATURE;
    nt->FileHeader.Machine=IMAGE_FILE_MACHINE_AMD64;
    nt->FileHeader.NumberOfSections=1;
    nt->FileHeader.SizeOfOptionalHeader=sizeof(IMAGE_OPTIONAL_HEADER64);
    nt->OptionalHeader.Magic=IMAGE_NT_OPTIONAL_HDR64_MAGIC;
    nt->OptionalHeader.SizeOfHeaders=0x400;
    nt->OptionalHeader.SizeOfImage=0x4000;
    uintptr_t base=(uintptr_t)memory;
    assert(szero_native_image(base,0x4000));
    assert(!szero_native_image(base,0x4001));
    assert(!szero_native_image(0,0));assert(!szero_native_image(1,0));
    const unsigned char code[]={0x48,0x89,0x5c,0x24};
    memcpy(memory+0x1000,code,sizeof(code));
    assert(szero_native_prefix(base,0x1000,code,sizeof(code)));
    memory[0x1002]^=1;assert(!szero_native_prefix(base,0x1000,code,sizeof(code)));
    memory[0x1002]^=1;
    assert(!szero_native_prefix(base,0x3fff,code,sizeof(code)));
    assert(!szero_native_prefix(base,SIZE_MAX-1,code,sizeof(code)));
    nt->FileHeader.Machine=IMAGE_FILE_MACHINE_I386;assert(!szero_native_image(base,0));
    nt->FileHeader.Machine=IMAGE_FILE_MACHINE_AMD64;
    nt->OptionalHeader.Magic=IMAGE_NT_OPTIONAL_HDR32_MAGIC;assert(!szero_native_image(base,0));
    nt->OptionalHeader.Magic=IMAGE_NT_OPTIONAL_HDR64_MAGIC;
    nt->OptionalHeader.SizeOfHeaders=0x10;assert(!szero_native_image(base,0));
    nt->OptionalHeader.SizeOfHeaders=0x400;
    nt->OptionalHeader.SizeOfImage=0x300;assert(!szero_native_image(base,0));
    nt->OptionalHeader.SizeOfImage=0x4000;
    dos->e_lfanew=-1;assert(!szero_native_image(base,0));
    dos->e_lfanew=0x100;dos->e_magic=0;assert(!szero_native_image(base,0));
    assert(VirtualFree(memory,0,MEM_RELEASE));
    puts("PE64 bounds and changed-instruction refusal passed without EXE hashing");
    return 0;
}
