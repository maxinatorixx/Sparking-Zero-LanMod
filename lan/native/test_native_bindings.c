/* Portable data-only PE fixture: never executes the synthetic instructions. */
#define SZERO_BINDINGS_PORTABLE_TEST 1
#define SZERO_BINDINGS_CATALOG "test_native_bindings_catalog.h"
#include "native_bindings.c"
#include <stdlib.h>
static void put16(unsigned char *p,uint16_t v){memcpy(p,&v,2);}
static void put32(unsigned char *p,uint32_t v){memcpy(p,&v,4);}
static void section(unsigned char *p,const char *name,uint32_t rva,uint32_t flags){
    memcpy(p,name,strlen(name));put32(p+8,0x1000);put32(p+12,rva);put32(p+36,flags);
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    const char *mode=argv[1];
    unsigned char *image=calloc(1,0x5000);
    if(!image)return 2;
    put16(image,0x5a4d);put32(image+60,0x80);put32(image+0x80,0x4550);
    put16(image+0x84,0x8664);put16(image+0x86,3);put16(image+0x94,240);
    put16(image+0x98,0x20b);put32(image+0x98+56,0x5000);put32(image+0x98+60,0x200);
    section(image+0x188,".text",0x1000,0x60000020);
    section(image+0x1b0,".rdata",0x2000,0x40000040);
    section(image+0x1d8,".data",0x3000,0xc0000040);
    int shift=!strcmp(mode,"shifted")?0x80:0;
    uint32_t code=0x1000+(uint32_t)shift,caller=0x1100+(uint32_t)shift,global=0x3000+(shift?0x100:0);
    memcpy(image+code,binding_bytes,17);put32(image+code+3,global-code-7);
    memcpy(image+caller,binding_bytes+34,10);put32(image+caller+1,code-caller-5);
    int expect=1;
    const char *error="ready_native_layout";
    if(!strcmp(mode,"ambiguous")) {memcpy(image+0x1300,image+code,17);expect=0;error="ambiguous_binding_0x1000";}
    if(!strcmp(mode,"changed_field")) {image[code+15]=0x28;expect=0;error="missing_binding_0x1000";}
    if(!strcmp(mode,"changed_branch")) {image[code+11]=0x04;expect=0;error="missing_binding_0x1000";}
    if(!strcmp(mode,"wrong_section")) {put32(image+code+3,0x2000-code-7);expect=0;error="wrong_binding_section_0x3000";}
    if(!strcmp(mode,"wrong_reference")) {put32(image+caller+1,code+16-caller-5);expect=0;error="binding_reference_mismatch_0x1100";}
    if(!strcmp(mode,"invalid_pe")) {put16(image+0x84,0x14c);expect=0;error="invalid_pe64";}
    if(!strcmp(mode,"out_of_bounds")) {put32(image+0x188+8,0x10000);expect=0;error="invalid_section_bounds";}
    int ok=szero_bindings_init_image((uintptr_t)image,0x5000);
    if(ok!=expect || strcmp(szero_bindings_error(),error)) {
        fprintf(stderr,"%s: ok=%d error=%s expected=%d/%s\n",mode,ok,szero_bindings_error(),expect,error);return 1;
    }
    if(ok) {
        if(szero_bind_rva(0x1000)!=code || szero_bind_rva(0x1100)!=caller || szero_bind_rva(0x3000)!=global || szero_bind_rva(0x9999))return 1;
        if(!szero_bind_prefix((uintptr_t)image,0x1000,binding_entries[0].prefix,17))return 1;
        put32(image+code+3,global+8-code-7);
        if(szero_bind_prefix((uintptr_t)image,0x1000,binding_entries[0].prefix,17))return 1;
        put32(image+code+3,global-code-7);
        image[code]=0xe9;
        if(szero_bind_prefix((uintptr_t)image,0x1000,binding_entries[0].prefix,17))return 1;
    } else if(szero_bind_rva(0x1000))return 1;
    free(image);
    puts(mode);
    return 0;
}
