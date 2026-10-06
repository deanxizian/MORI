#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#define MORI_AUDIO_SAMPLES 160
#define MORI_AUDIO_SLOTS 8
/* 10 ms, 16 kHz mono. Playback reference uses the DAC-consumed sample clock. */
typedef struct {uint32_t sequence;uint64_t captured_us;int16_t mic[160],reference[160];} mori_audio_frame_t;
typedef struct {mori_audio_frame_t frames[MORI_AUDIO_SLOTS];unsigned read,write,count,dropped;uint64_t played_samples;bool playing;} mori_audio_t;
bool mori_audio_push(mori_audio_t *a,const mori_audio_frame_t *f);
bool mori_audio_pop(mori_audio_t *a,mori_audio_frame_t *f,uint64_t now_us);
void mori_audio_played(mori_audio_t *a,size_t samples);
void mori_audio_interrupt(mori_audio_t *a);
