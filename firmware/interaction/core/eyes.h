#pragma once
#include <stdint.h>
#include <stdbool.h>
typedef struct {float x,y,a,b,c,d,w,h;} mori_eye_t;
typedef struct {int state;float start;bool transition;mori_eye_t from[2];} mori_eyes_t;
bool mori_eyes_sample(const mori_eyes_t *e,float seconds,float playback_rms,mori_eye_t out[2]);
bool mori_eyes_state(mori_eyes_t *e,int state,float seconds,float playback_rms);
/* RGB565, black exterior and 4% circle inset. Caller owns fixed-capacity buffer. */
void mori_eyes_render(const mori_eye_t eyes[2],uint16_t *buffer,int width,int height);

/* Skin boundary; alternative implementations keep clock, RMS and frame contracts. */
typedef struct {const char *id;bool (*sample)(const mori_eyes_t *,float,float,mori_eye_t[2]);void (*render)(const mori_eye_t[2],uint16_t *,int,int);} mori_eye_skin_t;
extern const mori_eye_skin_t mori_reference_skin;
