#include "sim_hal.h"
#include <string.h>
static uint64_t now(void *ctx){return ((sim_hal_t*)ctx)->clock;}
static void sample(void *ctx,mori_sample_t *out,mori_timing_t *t){
 sim_hal_t *s=ctx;*out=s->sample;out->imu_us=s->frame_begin-s->imu_age;
 out->monitor_us=s->frame_begin;float bat=0,ntc[2]={0};
 bool valid=mori_adc_voltage(s->battery_raw,s->battery_mv,&bat);
 for(int i=0;i<2;i++)valid=mori_adc_voltage(s->ntc_raw[i],s->ntc_mv[i],&ntc[i])&&valid;
 out->battery_v=bat*4;
 valid=mori_ntc(ntc[0],&out->temp_left_c)&&mori_ntc(ntc[1],&out->temp_right_c)&&valid;
 out->monitor_ok=out->monitor_ok&&valid;
 float speeds[2];const int signs[2]={1,-1};
 out->encoders_ok=mori_encoder_update(&s->encoders,s->counts,1.f/416,signs,speeds)&&out->encoders_ok;
 out->encoder_count[0]=s->counts[0];out->encoder_count[1]=s->counts[1];
 out->v_left=speeds[0];out->v_right=speeds[1];
 out->raw_accel[0]=out->ax;out->raw_accel[1]=out->ay;out->raw_accel[2]=out->az;out->raw_gyro[1]=out->gy;
 s->clock+=s->sample_cost;t->imu_io_us=s->sample_cost;t->wake_us=0;
}
static void apply(void *ctx,mori_output_t out){sim_hal_t *s=ctx;s->physical_output=out;s->apply_calls++;s->clock+=s->apply_cost;}
static void heartbeat(void *ctx,bool level){sim_hal_t *s=ctx;s->heartbeat=level;s->heartbeats++;}
void sim_hal_init(sim_hal_t *s){
 memset(s,0,sizeof(*s));s->clock=s->frame_begin=1000000;
 s->sample_cost=500;s->apply_cost=20;s->battery_raw=2300;s->battery_mv=1850;
 for(int i=0;i<2;i++){s->ntc_raw[i]=2000;s->ntc_mv[i]=1650;}
 s->sample=(mori_sample_t){.az=9.80665f,.imu_ok=true,.monitor_ok=true,.encoders_ok=true,.driver_ok=true,.estop_ok=true};
}
mori_hal_t sim_hal_interface(sim_hal_t *s){return(mori_hal_t){.context=s,.now_us=now,.sample=sample,.apply=apply,.heartbeat=heartbeat};}
void sim_tick(sim_hal_t *s,mori_runtime_t *r){s->frame_begin+=2404;s->clock=s->frame_begin;mori_hal_t h=sim_hal_interface(s);mori_runtime_frame(r,&h);}
