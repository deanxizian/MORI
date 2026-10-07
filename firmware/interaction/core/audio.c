#include "audio.h"
#include <string.h>
bool mori_audio_push(mori_audio_t *a,const mori_audio_frame_t *f){if(a->count==MORI_AUDIO_SLOTS){a->dropped++;return false;}a->frames[a->write]=*f;a->write=(a->write+1)%MORI_AUDIO_SLOTS;a->count++;return true;}
bool mori_audio_pop(mori_audio_t *a,mori_audio_frame_t *f,uint64_t now){while(a->count){*f=a->frames[a->read];a->read=(a->read+1)%MORI_AUDIO_SLOTS;a->count--;if(now>=f->captured_us&&now-f->captured_us<=80000)return true;a->dropped++;}return false;}
void mori_audio_played(mori_audio_t *a,size_t n){a->played_samples+=n;a->playing=true;}
void mori_audio_interrupt(mori_audio_t *a){a->count=a->read=a->write=0;a->playing=false;}
