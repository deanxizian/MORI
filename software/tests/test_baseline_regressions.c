/* Behavioral reproductions against the original snapshot; run before repairs. */
#include "mori_core.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
static int failures;
#define EXPECT(c, why) do { printf("%s %s\n", (c)?"PASS":"FAIL", why); if(!(c)) failures++; } while(0)
static mori_sample_t good(void) {
    return (mori_sample_t){.now_us=1000000,.imu_us=1000000,.monitor_us=1000000,
      .az=9.80665f,.battery_v=7.4f,.temp_left_c=25,.temp_right_c=25,
      .imu_ok=true,.monitor_ok=true,.encoders_ok=true,.driver_ok=true,.estop_ok=true};
}
int main(void) {
    mori_t m; mori_sample_t s=good(); mori_init(&m,(mori_config_t){0}); mori_step(&m,&s);
    mori_command(&m,(mori_command_t){.type=MC_CALIBRATE});
    /* One stationary sample repeatedly delivered must not satisfy a 1024-sample calibration. */
    for(int i=0;i<1024;i++) mori_step(&m,&s);
    EXPECT(!m.calibrated && m.state!=MORI_READY,"repeated timestamp cannot complete calibration");
    mori_init(&m,(mori_config_t){0}); /* independent first-cause fixture */
    mori_trip(&m,MF_ESTOP); mori_trip(&m,MF_TIMING);
    EXPECT(m.fault==MF_ESTOP,"first fault cause remains latched");
    mori_init(&m,(mori_config_t){0}); s=good(); mori_step(&m,&s);
    mori_command(&m,(mori_command_t){.type=MC_CALIBRATE});
    for(int i=0;i<1024;i++){s.now_us+=2404;s.imu_us=s.monitor_us=s.now_us;mori_step(&m,&s);}
    s.imu_ok=false;s.now_us+=2404;s.imu_us=s.monitor_us=s.now_us;mori_step(&m,&s);
    EXPECT(m.state==MORI_FAULT,"sensor failure in READY invalidates readiness and latches fault");
    /* Deadline polling at a healthy but slow 5.5ms frame cadence must not
       stretch the actual enabled interval beyond 200ms. */
    mori_init(&m,(mori_config_t){.power_verified=true});s=good();mori_step(&m,&s);
    mori_command(&m,(mori_command_t){.type=MC_CALIBRATE});
    for(int i=0;i<1024;i++){s.now_us+=2404;s.imu_us=s.monitor_us=s.now_us;mori_step(&m,&s);}
    mori_command(&m,(mori_command_t){.type=MC_ARM_BENCH});
    mori_command(&m,(mori_command_t){.type=MC_BENCH_DUTY,.a=.1f});
    s.now_us+=1000;s.imu_us=s.monitor_us=s.now_us;mori_step(&m,&s);uint64_t enabled_at=s.now_us;
    while(m.out.enable){s.now_us+=5500;s.imu_us=s.monitor_us=s.now_us;mori_step(&m,&s);}
    EXPECT(s.now_us-enabled_at<=200000,"bench enabled interval <=200ms with 5.5ms frame cadence");
    return failures?1:0;
}
