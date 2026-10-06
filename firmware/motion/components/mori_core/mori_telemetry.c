#include "mori_telemetry.h"
#include <inttypes.h>
void mori_log_snapshot(mori_log_t *l,const mori_runtime_t *r,uint32_t missed,uint32_t dropped,uint32_t parse_drops){
 *l=(mori_log_t){.sequence=r->frames,.sample=r->core.latest,.output=r->core.out,.state=r->core.state,.fault=r->core.fault,
 .pitch=r->core.theta,.timing=r->timing,.maxima=r->maxima,.missed=missed,.dropped=dropped,.overflows=atomic_load(&r->queue_overflows),
 .reply_drops=atomic_load(&r->reply_drops)+parse_drops,.cal_count=r->core.calibration_count,.head_enabled=r->head_active,
 .p50=mori_hist_quantile_upper(r->total_hist,50),.p95=mori_hist_quantile_upper(r->total_hist,95),.p99=mori_hist_quantile_upper(r->total_hist,99),
 .p99_wake=mori_hist_quantile_upper(r->wake_hist,99),.p99_jitter=mori_hist_quantile_upper(r->jitter_hist,99)};
}
void mori_log_print(FILE *f,const mori_log_t *l){
 fprintf(f,"DATA %"PRIu32",%"PRIu64",%s,%d,%.6f,%.5f,%.4f,%.4f,%.2f,%.2f,%.5f,%.5f,%u,",
 l->sequence,l->sample.now_us,mori_state_name(l->state),l->fault,l->pitch,(l->sample.v_left+l->sample.v_right)/2,
 l->sample.battery_v,l->sample.bus_a,l->sample.temp_left_c,l->sample.temp_right_c,l->output.left,l->output.right,l->output.enable);
 fprintf(f,"%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",",
 l->timing.total_us,l->timing.wake_us,l->timing.imu_io_us,l->timing.monitor_io_us,l->timing.encoder_us,l->timing.fusion_us,l->timing.feedback_us,l->timing.pwm_submit_us,l->timing.jitter_us,l->maxima.total_us,l->maxima.wake_us,l->maxima.jitter_us);
 fprintf(f,"%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%u,%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",%"PRIu32",",
 l->missed,l->dropped,l->overflows,l->reply_drops,l->cal_count,l->head_enabled,l->p50,l->p95,l->p99,l->p99_wake,l->p99_jitter);
 const mori_sample_t *s=&l->sample;
 fprintf(f,"%.5f,%.5f,%.5f,%.6f,%.5f,%.5f,%.5f,%.5f,%.5f,%.6f,%.6f,%.6f,%d,%u,%u,%u,%u,%u,%u,%u,%"PRId32",%"PRId32"\n",
 s->ax,s->ay,s->az,s->gy,s->v_left,s->v_right,s->raw_accel[0],s->raw_accel[1],s->raw_accel[2],s->raw_gyro[0],s->raw_gyro[1],s->raw_gyro[2],
 mori_health(s),s->driver_ok,s->estop_ok,s->imu_ok,s->monitor_ok,s->encoders_ok,l->output.low_battery,l->output.request_support,s->encoder_count[0],s->encoder_count[1]);

}
