#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "mori_core.h"
#include "wire.h"
#include "commands.h"
typedef enum { V1_COMPLETED,V1_RUNNING,V1_REJECTED,V1_EXPIRED,V1_CANCELLED,V1_FAULT } mori_v1_result_t;
/* Bounded idempotency window, matching the host executor's retained result count. */
#define MORI_V1_RESULT_CACHE 512u
typedef struct {uint64_t id;mori_v1_result_t result;} mori_v1_cached_result_t;
/* Adapters must honor torque_enabled independently of the position target. */
typedef struct {float position,velocity,target,minimum,maximum,zero,max_velocity,max_acceleration;int sign;bool verified,feedback_available,torque_enabled;} mori_axis_t;
typedef struct {
 mori_t core;mori_axis_t head[2];mori_wire_t wire;
 uint64_t session,lease_end_ms,last_id,last_ms;uint32_t sequence;
 bool claimed,maintenance,physical_contract_verified;float yaw_rate_target;
 mori_v1_cached_result_t results[MORI_V1_RESULT_CACHE];unsigned result_count,result_next;
 mori_v1_result_t last_result;unsigned rejected,dropped;
} mori_v1_t;
void mori_v1_init(mori_v1_t *v,uint64_t session);
bool mori_axis_target(mori_axis_t *a,float rad);
void mori_axis_step(mori_axis_t *a,float dt,bool inhibit);
mori_v1_result_t mori_v1_feed(mori_v1_t *v,uint8_t byte,uint64_t now_ms,bool *complete);
void mori_v1_tick(mori_v1_t *v,uint64_t now_ms,const mori_sample_t *sample);
