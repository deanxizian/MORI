#pragma once
#include "mori_protocol.h"
#include <stdatomic.h>
#define MORI_QUEUE_CAPACITY 8u
#define MORI_REPLY_CAPACITY 32u
#define MORI_COMPUTE_BUDGET_US 1800u
#define MORI_NOMINAL_PERIOD_US 2404u

typedef struct {
 uint32_t imu_io_us,monitor_io_us,encoder_us,wake_us,core_us,fusion_us,feedback_us,pwm_submit_us,total_us,jitter_us;
} mori_timing_t;
typedef struct {void *context;uint64_t (*now_us)(void *);void (*sample)(void *,mori_sample_t *,mori_timing_t *);void (*apply)(void *,mori_output_t);void (*heartbeat)(void *,bool);void (*after_apply)(void *);} mori_hal_t;
typedef struct {uint32_t id;mori_request_kind_t kind;mori_reason_t reason;mori_state_t state;mori_fault_t fault;} mori_reply_t;
typedef struct {
 mori_t core;
 mori_request_t requests[MORI_QUEUE_CAPACITY]; atomic_uint write_index,read_index;
 mori_reply_t replies[MORI_REPLY_CAPACITY]; atomic_uint reply_write,reply_read;
 atomic_bool queue_fault; atomic_uint queue_overflows,reply_drops;
 bool head_verified,axes_verified,head_active,heartbeat_level;float head_target;uint32_t head_revision;
 uint64_t previous_begin;uint32_t frames;
 mori_timing_t timing,maxima;
 /* All-frame upper-bound histogram buckets: 100us,200us,...3200us,overflow. */
 uint32_t total_hist[33],wake_hist[33],jitter_hist[33];
} mori_runtime_t;
void mori_runtime_init(mori_runtime_t *r,mori_config_t config,bool head_verified,bool axes_verified);
/* One command producer, one frame consumer; one reply producer, one logger consumer. */
bool mori_runtime_enqueue(mori_runtime_t *r,mori_request_t request);
bool mori_runtime_reply(mori_runtime_t *r,mori_reply_t *reply);
void mori_runtime_frame(mori_runtime_t *r,const mori_hal_t *hal);
uint32_t mori_hist_quantile_upper(const uint32_t histogram[33],unsigned percent);
