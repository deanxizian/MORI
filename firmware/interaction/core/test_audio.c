#include "audio.h"
#include <assert.h>
#include <stdio.h>
int main(void){mori_audio_t audio={0};mori_audio_frame_t f={.captured_us=10000,.sequence=1},out={0};f.mic[0]=111;f.reference[0]=222;
 for(int i=0;i<8;i++)assert(mori_audio_push(&audio,&f));
 assert(!mori_audio_push(&audio,&f));assert(audio.dropped==1);
 assert(mori_audio_pop(&audio,&out,20000));assert(out.mic[0]==111&&out.reference[0]==222);
 assert(!mori_audio_pop(&audio,&out,100000));assert(audio.dropped==8);
 mori_audio_played(&audio,160);assert(audio.played_samples==160&&audio.playing);mori_audio_interrupt(&audio);assert(!audio.playing&&audio.count==0);
 puts("PASS bounded audio queue, separate AEC reference, stale/drop counters, consumed playback clock and interruption; HOST only");return 0;}
