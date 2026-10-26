/* Native-thread-only applied snapshots. Never accessed by the socket worker.
 * Equality avoids resetting native-owned stream cursors on unchanged polls. */
#ifndef SZERO_NATIVE_SESSION_FRAMES_INC
#define SZERO_NATIVE_SESSION_FRAMES_INC
static struct {
 uintptr_t service;
 size_t size;
 unsigned char frame[SZERO_SESSION_FRAME_MAX];
} provider_applied_frames[4];
static size_t provider_frame_size(const char *frame) {
 if(!frame) return 0;
 for(size_t size=0;size<SZERO_SESSION_FRAME_MAX;size++) if(!frame[size]) return size;
 return 0;
}
static int provider_frame_same(uintptr_t service,const char *frame) {
 size_t size=provider_frame_size(frame);
 if(!service || !size) return 0;
 for(unsigned i=0;i<4;i++) if(provider_applied_frames[i].service==service)
  return provider_applied_frames[i].size==size && !memcmp(provider_applied_frames[i].frame,frame,size);
 return 0;
}
static int provider_frame_mark(uintptr_t service,const char *frame) {
 size_t size=provider_frame_size(frame);unsigned available=4;
 if(!service || !size) return 0;
 for(unsigned i=0;i<4;i++) {
  if(provider_applied_frames[i].service==service) {available=i;break;}
  if(!provider_applied_frames[i].service && available==4) available=i;
 }
 if(available==4) return 0;
 memcpy(provider_applied_frames[available].frame,frame,size);
 provider_applied_frames[available].frame[size]=0;
 provider_applied_frames[available].size=size;
 provider_applied_frames[available].service=service;
 return 1;
}
static void provider_frame_clear(uintptr_t service) {
#ifdef SZERO_NATIVE_USERINFO_PROVIDER
 userinfo_clear(service);
#endif
 for(unsigned i=0;i<4;i++) if(provider_applied_frames[i].service==service)
  memset(&provider_applied_frames[i],0,sizeof(provider_applied_frames[i]));
}
#endif
