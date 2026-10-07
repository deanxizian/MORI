#pragma once
#include "mori_runtime.h"
#include <stdio.h>
#define MORI_CSV_HEADER "seq,device_us,state,fault,pitch_rad,v_m_s,bat_V,bus_A,TL_C,TR_C,uL,uR,enabled,run_us,wake_us,imu_io_us,monitor_io_us,encoder_us,fusion_us,feedback_us,pwm_submit_us,jitter_us,max_run_us,max_wake_us,max_jitter_us,sample_missed,log_dropped,command_overflows,reply_dropped,cal_count,head_enabled,p50_run_upper_us,p95_run_upper_us,p99_run_upper_us,p99_wake_upper_us,p99_jitter_upper_us,ax_m_s2,ay_m_s2,az_m_s2,gy_rad_s,vL_m_s,vR_m_s,raw_ax_m_s2,raw_ay_m_s2,raw_az_m_s2,raw_gx_rad_s,raw_gy_rad_s,raw_gz_rad_s,health_fault,driver_ok,estop_ok,imu_ok,monitor_ok,encoders_ok,low_battery,request_support,encoder_count_L,encoder_count_R"
typedef struct {
 uint32_t sequence;mori_sample_t sample;mori_output_t output;mori_state_t state;mori_fault_t fault;
 float pitch;mori_timing_t timing,maxima;uint32_t missed,dropped,overflows,reply_drops,cal_count;bool head_enabled;
 uint32_t p50,p95,p99,p99_wake,p99_jitter;
} mori_log_t;
void mori_log_snapshot(mori_log_t *log,const mori_runtime_t *runtime,uint32_t missed,uint32_t dropped,uint32_t parser_reply_drops);
/* Low-priority logger or host simulator ONLY. */
void mori_log_print(FILE *stream,const mori_log_t *log);
