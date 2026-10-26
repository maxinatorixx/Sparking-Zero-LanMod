#include "backend_response.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint64_t before;
    SzeroBackendView view;
    uint64_t after;
    unsigned created,projected,streams,headers;
    unsigned fail_create,parser_error,move_owner;
    const unsigned char *body;
    size_t body_size;
    uintptr_t projected_owner;
} Test;
static SzeroBackendView *create(void *context) {
    Test *t=context;
    ++t->created;
    if(t->fail_create) return NULL;
    memset(&t->view,0,sizeof(t->view));
    t->view.vtable=0x146d36f80;
    return &t->view;
}
static void project(void *context,void *output,SzeroBackendRaw *raw) {
    Test *t=context;
    unsigned char *out=output;
    ++t->projected;
    assert(raw->status==200 && !raw->padding);
    assert(raw->headers.buckets==(uintptr_t)&raw->headers.inline_bucket);
    assert(raw->headers.bucket_count==1 && !raw->headers.count);
    assert(!raw->headers.head && !raw->headers.inline_bucket);
    assert(!raw->stream.allocator && raw->stream.object==(uintptr_t)&t->view);
    assert(t->view.vtable==0x146d36f80 && !t->view.reserved);
    assert(!t->view.read_cursor && t->view.size==t->body_size);
    assert(t->view.data==(uintptr_t)t->body);
    assert(!memcmp((void *)t->view.data,t->body,t->body_size));
    memset(out,0,SZERO_BACKEND_PROJECTED_SIZE);
    out[0]=(unsigned char)(t->parser_error?1:2);
    if(t->parser_error) { uint32_t code=0x57c77900;memcpy(out+8,&code,4); }
    else memcpy(out+64,&t->projected_owner,sizeof(t->projected_owner));
    if(t->move_owner) raw->stream.object=0;
}
static void stream(void *context,SzeroBackendOwner *owner) {
    Test *t=context;
    ++t->streams;
    assert(t->projected==1 && t->headers==0);
    assert(!owner->allocator);
    assert(owner->object==(t->move_owner?0:(uintptr_t)&t->view));
    owner->object=0;
}
static void headers(void *context,SzeroBackendHeaders *map) {
    Test *t=context;
    ++t->headers;
    assert(t->streams==1);
    assert(map->buckets==(uintptr_t)&map->inline_bucket);
}
static void initialize(Test *t,const unsigned char *body,size_t size) {
    memset(t,0,sizeof(*t));
    t->before=0x1122334455667788;t->after=0x8877665544332211;
    t->body=body;t->body_size=size;t->projected_owner=0x123456789abcdef0;
}
static SzeroBackendResponseFunctions callbacks(Test *t) {
    return (SzeroBackendResponseFunctions){t,create,project,stream,headers};
}
int main(void) {
    unsigned char body[SZERO_BACKEND_BODY_MAX],original[SZERO_BACKEND_BODY_MAX];
    struct { unsigned char before[16],output[72],after[16]; } guarded;
    Test t;
    memset(body,'x',sizeof(body));memcpy(body,"{}",2);
    memcpy(original,body,sizeof(body));
    for(unsigned mode=0;mode<4;++mode) {
        initialize(&t,body,mode==3?sizeof(body):2);
        t.parser_error=mode==1;t.move_owner=mode==2;
        SzeroBackendResponseFunctions f=callbacks(&t);
        memset(&guarded,0xa5,sizeof(guarded));
        assert(szero_backend_response_project(guarded.output,72,body,t.body_size,&f));
        assert(t.created==1 && t.projected==1 && t.streams==1 && t.headers==1);
        assert(guarded.output[0]==(t.parser_error?1:2));
        if(t.parser_error) {uint32_t code;memcpy(&code,guarded.output+8,4);assert(code==0x57c77900);}
        else {uintptr_t owner;memcpy(&owner,guarded.output+64,8);assert(owner==t.projected_owner);}
        for(unsigned i=0;i<16;++i) assert(guarded.before[i]==0xa5 && guarded.after[i]==0xa5);
        assert(t.before==0x1122334455667788 && t.after==0x8877665544332211);
        assert(!memcmp(original,body,sizeof(body)));
    }
    initialize(&t,body,2);
    SzeroBackendResponseFunctions f=callbacks(&t);
    memset(&guarded,0xa5,sizeof(guarded));
    assert(!szero_backend_response_project(NULL,72,body,2,&f));
    assert(!szero_backend_response_project(guarded.output,71,body,2,&f));
    assert(!szero_backend_response_project(guarded.output,72,NULL,2,&f));
    assert(!szero_backend_response_project(guarded.output,72,body,0,&f));
    assert(!szero_backend_response_project(guarded.output,72,body,sizeof(body)+1,&f));
    assert(!szero_backend_response_project(guarded.output,72,body,SIZE_MAX,&f));
    assert(!szero_backend_response_project(guarded.output,72,(const unsigned char *)UINTPTR_MAX,2,&f));
    assert(!szero_backend_response_project((void *)UINTPTR_MAX,72,body,2,&f));
    assert(!szero_backend_response_project(guarded.output,72,body,2,NULL));
    for(unsigned i=0;i<4;++i) {
        SzeroBackendResponseFunctions bad=f;
        if(i==0)bad.create_view=NULL;
        if(i==1)bad.project=NULL;
        if(i==2)bad.release_stream=NULL;
        if(i==3)bad.release_headers=NULL;
        assert(!szero_backend_response_project(guarded.output,72,body,2,&bad));
    }
    assert(!t.created && !t.projected && !t.streams && !t.headers);
    t.fail_create=1;
    assert(!szero_backend_response_project(guarded.output,72,body,2,&f));
    assert(t.created==1 && !t.projected && !t.streams && !t.headers);
    for(size_t i=0;i<sizeof(guarded);++i)assert(((unsigned char *)&guarded)[i]==0xa5);
    puts("Native backend response projection contracts passed");
    return 0;
}
