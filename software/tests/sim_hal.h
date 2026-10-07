#pragma once
#include "mori_runtime.h"
#include "mori_io.h"
/* Explicit deterministic virtual time and fake actuators. No device IO. */
typedef struct {
 uint64_t clock,frame_begin,imu_age;
 uint32_t sample_cost,apply_cost,heartbeats,apply_calls;
 int32_t counts[2];mori_encoder_t encoders;
 int battery_raw,battery_mv,ntc_raw[2],ntc_mv[2];
 mori_sample_t sample;mori_output_t physical_output;bool heartbeat;
} sim_hal_t;
void sim_hal_init(sim_hal_t *s);
mori_hal_t sim_hal_interface(sim_hal_t *s);
void sim_tick(sim_hal_t *s,mori_runtime_t *runtime);
