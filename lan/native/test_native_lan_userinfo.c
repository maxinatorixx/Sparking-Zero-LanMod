#include "native_lan_userinfo.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
typedef struct {uintptr_t p;size_t n;int write;} Range;
typedef struct {
 Range ranges[24];size_t count;unsigned calls,ready;
 const void *expect_ids;int native_failure,copy_failure,consume;
 unsigned copies,destroys;
} Fixture;
static const char first[]="szlan:11111111111111111111111111111111";
static const char second[]="szlan:22222222222222222222222222222222";
static const char unknown[]="szlan:33333333333333333333333333333333";
static void region(Fixture *f,void *p,size_t n,int write) {assert(f->count<24);f->ranges[f->count++]=(Range){(uintptr_t)p,n,write};}
static int range(Fixture *f,uintptr_t p,size_t n,int writing) {
 for(size_t i=0;i<f->count;i++) {
  Range r=f->ranges[i];
  if(p>=r.p && p-r.p<=r.n && n<=r.n-(p-r.p) && (!writing || r.write)) return 1;
 }
 return 0;
}
static int read_owned(void *c,uintptr_t p,void *out,size_t n) {if(!range(c,p,n,0)) return 0;memcpy(out,(void *)p,n);return 1;}
static int writable(void *c,uintptr_t p,size_t n) {return range(c,p,n,1);}
static void write_owned(void *c,uintptr_t p,const void *in,size_t n) {assert(range(c,p,n,1));memcpy((void *)p,in,n);}
static int ready(void *c) {return ((Fixture *)c)->ready;}
static int known(void *c,const unsigned char principal[38]) {(void)c;return !memcmp(principal,first,38)||!memcmp(principal,second,38);}
static int copy_id(void *context,SzeroNativeString *out,const SzeroNativeString *in) {
 Fixture *f=context;if(f->copy_failure) return 0;f->copies++;
 *out=*in;
 if(in->words[0]&1) {
  void *p=malloc((size_t)in->words[2]+1);assert(p);
  memcpy(p,(void *)in->words[1],(size_t)in->words[2]);((char *)p)[in->words[2]]=0;
  out->words[1]=(uintptr_t)p;
 }
 return 1;
}
static void destroy_id(void *context,SzeroNativeString *owned) {
 ((Fixture *)context)->destroys++;
 if(owned->words[0]&1) free((void *)owned->words[1]);
 memset(owned,0,sizeof(*owned));
}
static void string(SzeroNativeString *out,const char *p) {
 memset(out,0,sizeof(*out));size_t n=strlen(p);
 if(n>30) {out->words[0]=1;out->words[1]=(uintptr_t)p;out->words[2]=out->words[3]=n;}
 else {unsigned char *b=(unsigned char *)out;b[0]=(unsigned char)(n<<2);memcpy(b+1,p,n);}
}
static void *original(void *context,void *self,void *out,const void *ids,void *records) {
 Fixture *f=context;assert(self==f);f->calls++;
 if(f->expect_ids) assert(ids==f->expect_ids);
 SzeroUserInfoVector input;memcpy(&input,ids,sizeof(input));
 for(size_t i=0;i<input.count;i++) {
  const SzeroNativeString *s=(void *)(input.data+i*32);
  const char *p=(s->words[0]&1)?(void *)s->words[1]:(const char *)s+1;
  assert(strncmp(p,"szlan:",6)); /* Never give LAN identities to platform. */
 }
 memset(out,0,48);
 if(f->native_failure) {uint32_t tag=1,code=0x12345600;memcpy(out,&tag,4);memcpy((char *)out+8,&code,4);return out;}
 SzeroUserInfoVector rows=*(SzeroUserInfoVector *)records;
 if(f->consume) {
  /* Model the audited original's move-and-erase contract: one independently
   * owned real ID transfers to native rows, then source count becomes zero. */
  assert(input.count==1 && rows.count<rows.capacity);
  SzeroNativeString *owned=(void *)input.data;
  SzeroUserInfoRecord *target=(void *)(rows.data+rows.count*40);
  target->id=*owned;target->flags=4;
  memset(owned,0,sizeof(*owned));
  ((SzeroUserInfoVector *)ids)->count=0;rows.count++;
 }
 for(size_t i=0;i<rows.count;i++) {
  SzeroUserInfoRecord *r=(void *)(rows.data+i*40);
  const char *p=(r->id.words[0]&1)?(void *)r->id.words[1]:(const char *)&r->id+1;
  if(strncmp(p,"szlan:",6)) r->flags=4;
 }
 uint32_t tag=2;memcpy(out,&tag,4);memcpy((char *)out+8,&rows,sizeof(rows));
 memset(records,0,sizeof(rows));return out;
}
static SzeroUserInfoCallbacks callbacks(Fixture *f) {
 SzeroUserInfoCallbacks cb={f,read_owned,writable,write_owned,ready,known,copy_id,destroy_id,original};return cb;
}
int main(void) {
 Fixture f={0};f.ready=1;
 SzeroNativeString ids[2];string(ids,first);string(ids+1,"76561198000000000");
 SzeroUserInfoRecord rows[2]={0};rows[0].id=ids[0];rows[0].flags=255;rows[1].id=ids[1];rows[1].flags=13;
 SzeroUserInfoVector input={(uintptr_t)ids,1,2},records={(uintptr_t)rows,2,2};
 struct {unsigned char left[8],out[48],right[8];} guarded;memset(&guarded,0xa5,sizeof(guarded));
 region(&f,ids,sizeof(ids),0);region(&f,&input,sizeof(input),0);region(&f,&records,sizeof(records),1);
 region(&f,rows,sizeof(rows),1);region(&f,guarded.out,sizeof(guarded.out),1);
 region(&f,(void *)first,sizeof(first),0);region(&f,(void *)second,sizeof(second),0);region(&f,(void *)unknown,sizeof(unknown),0);
 SzeroUserInfoCallbacks cb=callbacks(&f);
 SzeroNativeString before[2];memcpy(before,ids,sizeof(ids));
 assert(szero_lan_userinfo_dispatch(&f,guarded.out,&input,&records,&cb)==SZERO_USERINFO_LAN);
 assert(!f.calls && !records.data && !records.count && !records.capacity);
 assert(rows[0].flags==0 && rows[1].flags==13 && !memcmp(before,ids,sizeof(ids)));
 SzeroUserInfoVector moved;memcpy(&moved,guarded.out+8,sizeof(moved));assert(moved.data==(uintptr_t)rows && moved.count==2);
 assert(*(uint32_t *)guarded.out==2);
 for(size_t i=0;i<8;i++) assert(guarded.left[i]==0xa5 && guarded.right[i]==0xa5);
 /* Mixed call delegates only the real subset, preserving native ownership and
  * real-ID status. Input snapshots are never consumed or native-destructed. */
 input.count=2;records=moved;rows[0].flags=255;
 assert(szero_lan_userinfo_dispatch(&f,guarded.out,&input,&records,&cb)==SZERO_USERINFO_DELEGATED);
 assert(f.calls==1 && !records.data && rows[0].flags==0 && rows[1].flags==4);
 assert(f.copies==1 && f.destroys==1);
 assert(!memcmp(before,ids,sizeof(ids)));
 /* All-real calls are exact forwarding even if LAN thread/readiness fails. */
 input.data=(uintptr_t)(ids+1);input.count=input.capacity=1;records=moved;
 f.ready=0;f.expect_ids=&input;
 assert(szero_lan_userinfo_dispatch(&f,guarded.out,&input,&records,&cb)==SZERO_USERINFO_DELEGATED);
 assert(f.calls==2);f.expect_ids=NULL;
 input.data=(uintptr_t)ids;input.count=1;input.capacity=2;records=moved;
 unsigned char output_before[48];memcpy(output_before,guarded.out,48);
 SzeroUserInfoRecord rows_before[2];memcpy(rows_before,rows,sizeof(rows));
#define REFUSE() do { \
 assert(szero_lan_userinfo_dispatch(&f,guarded.out,&input,&records,&cb)==SZERO_USERINFO_REFUSED); \
 assert(!memcmp(output_before,guarded.out,48) && !memcmp(rows_before,rows,sizeof(rows)) && !memcmp(&records,&moved,sizeof(records))); \
 assert(f.calls==2); \
} while(0)
 REFUSE();f.ready=1;
 string(ids,unknown);REFUSE();
 string(ids,"szlan:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");REFUSE();
 string(ids,"szlan:");REFUSE();
 string(ids,first);ids[0].words[1]=UINTPTR_MAX-4;REFUSE();string(ids,first);
 input.count=3;REFUSE();input.count=1;
 input.data=UINTPTR_MAX-15;REFUSE();input.data=(uintptr_t)ids;
 f.ranges[3].write=0;REFUSE();f.ranges[3].write=1;
 f.ranges[4].write=0;REFUSE();f.ranges[4].write=1;
 rows[0].id=ids[1];memcpy(rows_before,rows,sizeof(rows));REFUSE();rows[0].id=ids[0];memcpy(rows_before,rows,sizeof(rows));
 input.count=2;string(ids+1,first);REFUSE();string(ids+1,"76561198000000000");input.count=1;
 /* An original platform error is never manufactured into LAN success. */
 input.count=2;f.native_failure=1;
 assert(szero_lan_userinfo_dispatch(&f,guarded.out,&input,&records,&cb)==SZERO_USERINFO_DELEGATED);
 assert(*(uint32_t *)guarded.out==1 && *(uint32_t *)(guarded.out+8)==0x12345600 && f.calls==3);
 /* Exercise heap-owned real-ID moves, not just inline status updates. */
 f.native_failure=0;f.consume=1;
 const char heap_real[]="7656119800000000012345678901234567890";
 region(&f,(void *)heap_real,sizeof(heap_real),0);
 string(ids+1,heap_real);
 SzeroUserInfoRecord moved_rows[3]={0};moved_rows[0].id=ids[0];moved_rows[0].flags=255;
 region(&f,moved_rows,sizeof(moved_rows),1);
 records=(SzeroUserInfoVector){(uintptr_t)moved_rows,1,3};
 input.count=2;memcpy(before,ids,sizeof(ids));
 assert(szero_lan_userinfo_dispatch(&f,guarded.out,&input,&records,&cb)==SZERO_USERINFO_DELEGATED);
 memcpy(&moved,guarded.out+8,sizeof(moved));
 assert(moved.count==2 && !records.data && !memcmp(before,ids,sizeof(ids)));
 assert(moved_rows[1].id.words[1]!=(uintptr_t)heap_real);
 assert(!memcmp((void *)moved_rows[1].id.words[1],heap_real,strlen(heap_real)));
 destroy_id(&f,&moved_rows[1].id);
 for(size_t i=0;i<8;i++) assert(guarded.left[i]==0xa5 && guarded.right[i]==0xa5);
#undef REFUSE
 puts("LAN userinfo namespace and native ownership contracts passed; synthetic memory only");
 return 0;
}
