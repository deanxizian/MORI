#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef struct {float position,velocity;} mori_head_trajectory_t;
void mori_head_step(mori_head_trajectory_t *head,float target,float dt);
float mori_head_pulse_us(float head_deg);
/* Resolution independent, RGB565; circular crop outside min(width,height)/2. */
uint16_t mori_face_pixel(unsigned width,unsigned height,unsigned x,unsigned y,bool fault,bool blink);

typedef struct {bool blocked;uint32_t blocked_revision;} mori_head_guard_t;
bool mori_head_guard(mori_head_guard_t *guard,uint32_t revision,bool enabled,bool fresh,float dt);
