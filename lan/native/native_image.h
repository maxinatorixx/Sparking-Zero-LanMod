#ifndef SZERO_NATIVE_IMAGE_H
#define SZERO_NATIVE_IMAGE_H
/* Validate the loaded PE64 image, never the executable's on-disk digest.
 * A required RVA extent bounds fixed-offset reads before layout checks. */
#include <windows.h>
#include <stdint.h>
#include <string.h>

static inline int szero_native_image(uintptr_t base, SIZE_T required_extent) {
    IMAGE_DOS_HEADER dos;
    IMAGE_NT_HEADERS64 nt;
    SIZE_T got=0;
    if(!base || !ReadProcessMemory(GetCurrentProcess(),(void *)base,&dos,sizeof(dos),&got) ||
       got!=sizeof(dos) || dos.e_magic!=IMAGE_DOS_SIGNATURE || dos.e_lfanew<=0 ||
       (unsigned)dos.e_lfanew>1024*1024 || base>UINTPTR_MAX-(unsigned)dos.e_lfanew)
        return 0;
    if(!ReadProcessMemory(GetCurrentProcess(),(void *)(base+(unsigned)dos.e_lfanew),&nt,sizeof(nt),&got) ||
       got!=sizeof(nt) || nt.Signature!=IMAGE_NT_SIGNATURE ||
       nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64 ||
       nt.FileHeader.SizeOfOptionalHeader<sizeof(IMAGE_OPTIONAL_HEADER64) ||
       nt.OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
       !nt.FileHeader.NumberOfSections ||
       nt.OptionalHeader.SizeOfHeaders<(unsigned)dos.e_lfanew+sizeof(nt) ||
       nt.OptionalHeader.SizeOfImage<nt.OptionalHeader.SizeOfHeaders ||
       nt.OptionalHeader.SizeOfImage<required_extent ||
       base>UINTPTR_MAX-nt.OptionalHeader.SizeOfImage)
        return 0;
    return 1;
}

static inline int szero_native_prefix(uintptr_t base, SIZE_T rva,
                                     const unsigned char *prefix, SIZE_T length) {
    unsigned char actual[32];
    SIZE_T got=0;
    if(!prefix || !length || length>sizeof(actual) || rva>SIZE_MAX-length ||
       !szero_native_image(base,rva+length))return 0;
    return ReadProcessMemory(GetCurrentProcess(),(void *)(base+rva),actual,length,&got) &&
           got==length && !memcmp(actual,prefix,length);
}
#endif
