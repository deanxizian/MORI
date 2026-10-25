/* SIMULATED INPUT ONLY: not a motor, battery, IMU, or balance test. */
#include "mori_core.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
static int checks;
#define CHECK(c) do{assert(c);checks++;}while(0)
static mori_sample_t healthy(void){return (mori_sample_t){.now_us=1000000,.imu_us=1000000,.monitor_us=1000000,.az=9.80665f,.battery_v=7.4f,.temp_left_c=25,.temp_right_c=25,.imu_ok=true,.monitor_ok=true,.encoders_ok=true,.driver_ok=true,.estop_ok=true};}
static void tick(mori_t*m,mori_sample_t*s){s->now_us+=2404;s->imu_us=s->monitor_us=s->now_us;mori_step(m,s);}
static void init_ready(mori_t*m,mori_sample_t*s){
 mori_init(m,(mori_config_t){.power_verified=true,.balance_enabled=true});*s=healthy();mori_step(m,s);
 CHECK(mori_command(m,(mori_command_t){.type=MC_CALIBRATE}));
 for(int i=0;i<1023;i++)tick(m,s);CHECK(!m->calibrated);tick(m,s);CHECK(m->state==MORI_READY);
 CHECK(mori_command(m,(mori_command_t){.type=MC_CONFIRM_SIGNS}));
 /* Arbitrary test-only gains exercise safety code; never delivered as tuning. */
 CHECK(mori_command(m,(mori_command_t){.type=MC_GAINS,.a=1,.b=.05f,.c=.1f,.d=.01f}));
}
static void balance(mori_t*m,mori_sample_t*s){init_ready(m,s);CHECK(mori_command(m,(mori_command_t){.type=MC_ARM_BALANCE}));tick(m,s);CHECK(m->out.enable);}
int main(void){
 mori_t m;mori_sample_t s=healthy();mori_init(&m,(mori_config_t){0});mori_step(&m,&s);
 CHECK(!m.out.enable);CHECK(!mori_command(&m,(mori_command_t){.type=MC_ARM_BENCH}));CHECK(!mori_command(&m,(mori_command_t){.type=MC_ARM_BALANCE}));
 init_ready(&m,&s);CHECK(mori_command(&m,(mori_command_t){.type=MC_ARM_BENCH}));CHECK(!mori_command(&m,(mori_command_t){.type=MC_BENCH_DUTY,.a=.13}));
 CHECK(mori_command(&m,(mori_command_t){.type=MC_BENCH_DUTY,.a=.10,.b=-.10}));tick(&m,&s);CHECK(m.out.enable&&m.out.left>.09);
 for(int i=0;i<90;i++)tick(&m,&s);CHECK(m.state==MORI_READY&&!m.out.enable);
 balance(&m,&s);CHECK(mori_command(&m,(mori_command_t){.type=MC_MOVE,.a=.1,.b=.03}));tick(&m,&s);CHECK(m.v_ref>0);
 CHECK(mori_command(&m,(mori_command_t){.type=MC_STOP}));tick(&m,&s);CHECK(m.state==MORI_BALANCE&&m.out.enable&&m.v_target==0);
 CHECK(mori_command(&m,(mori_command_t){.type=MC_MOVE,.a=.1}));for(int i=0;i<215;i++)tick(&m,&s);CHECK(m.state==MORI_BALANCE&&m.v_target==0&&m.out.enable);
 balance(&m,&s);s.estop_ok=false;tick(&m,&s);CHECK(m.state==MORI_FAULT&&!m.out.enable);s.estop_ok=true;tick(&m,&s);CHECK(m.state==MORI_FAULT);CHECK(!mori_command(&m,(mori_command_t){.type=MC_DISARM}));CHECK(mori_command(&m,(mori_command_t){.type=MC_ACK}));CHECK(m.state==MORI_DISARMED&&!m.calibrated);
 for(int k=0;k<8;k++){
  balance(&m,&s);
  switch(k){case 0:s.imu_ok=false;break;case 1:s.driver_ok=false;break;case 2:s.encoders_ok=false;break;case 3:s.battery_v=5.9;break;case 4:s.bus_a=1.4;break;case 5:s.temp_left_c=70;break;case 6:s.ax=NAN;break;case 7:s.monitor_ok=false;break;}
  tick(&m,&s);CHECK(m.state==MORI_FAULT&&!m.out.enable);CHECK(m.out.left==0&&m.out.right==0);
 }
 balance(&m,&s);s.now_us+=9000;s.monitor_us=s.now_us;mori_step(&m,&s);CHECK(m.fault==MF_SENSOR&&!m.out.enable);
 balance(&m,&s);s.battery_v=6.7;tick(&m,&s);CHECK(m.state==MORI_BALANCE&&m.out.low_battery);CHECK(!mori_command(&m,(mori_command_t){.type=MC_MOVE,.a=.1}));s.battery_v=6.5;tick(&m,&s);CHECK(m.out.request_support&&m.out.enable);
 balance(&m,&s);m.theta=.4;tick(&m,&s);CHECK(m.fault==MF_TILT&&!m.out.enable);
 balance(&m,&s);m.cfg.kp=10;m.theta=.15;s.v_left=s.v_right=.02;for(int i=0;i<90;i++){m.theta=.15;tick(&m,&s);}CHECK(m.fault==MF_SATURATION&&!m.out.enable);
 balance(&m,&s);s.now_us+=7000;s.imu_us=s.monitor_us=s.now_us;mori_step(&m,&s);CHECK(m.fault==MF_TIMING&&!m.out.enable);
 balance(&m,&s);CHECK(!mori_command(&m,(mori_command_t){.type=MC_MOVE,.a=NAN}));CHECK(!mori_command(&m,(mori_command_t){.type=MC_GAINS,.a=2,.b=.1}));
 mori_init(&m,(mori_config_t){0});s=healthy();mori_step(&m,&s);CHECK(mori_command(&m,(mori_command_t){.type=MC_CALIBRATE}));for(int i=0;i<1100;i++){s.gy=.20;tick(&m,&s);}CHECK(!m.calibrated&&m.state==MORI_CALIBRATING);
 printf("PASS %d assertions; simulated-input safety/state tests only\n",checks);return 0;
}
