#include "sim_hal.h"
#include "mori_ui.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(c) do {checks++;if(!(c)){fprintf(stderr,"FAIL %s:%d: %s\n",__FILE__,__LINE__,#c);exit(1);}}while(0)
static void drain(mori_runtime_t *r){mori_reply_t reply;while(mori_runtime_reply(r,&reply)){} }
static void command(sim_hal_t *s,mori_runtime_t *r,const char *line){
 mori_request_t req;CHECK(mori_parse(line,&req)==MR_OK);CHECK(mori_runtime_enqueue(r,req));sim_tick(s,r);
 mori_reply_t reply;CHECK(mori_runtime_reply(r,&reply));CHECK(reply.reason==MR_OK);drain(r);
}
static void ready(sim_hal_t *s,mori_runtime_t *r){
 sim_hal_init(s);mori_runtime_init(r,(mori_config_t){.power_verified=true,.balance_enabled=true},true,true);
 sim_tick(s,r);command(s,r,"calibrate");for(int i=0;i<1024;i++)sim_tick(s,r);
 CHECK(r->core.state==MORI_READY);CHECK(!s->physical_output.enable);
}
static void balance(sim_hal_t *s,mori_runtime_t *r){
 ready(s,r);command(s,r,"confirm_signs");command(s,r,"gains 1 .05 .1 .01");command(s,r,"arm balance");sim_tick(s,r);
 CHECK(s->physical_output.enable);CHECK(r->core.state==MORI_BALANCE);
}
static void assert_latched(sim_hal_t *s,mori_runtime_t *r,mori_fault_t fault){
 CHECK(r->core.state==MORI_FAULT);CHECK(r->core.fault==fault);CHECK(!s->physical_output.enable);
 CHECK(s->physical_output.left==0&&s->physical_output.right==0);
 uint32_t heartbeats=s->heartbeats;
 for(int i=0;i<4;i++)sim_tick(s,r);
 CHECK(s->heartbeats==heartbeats);CHECK(r->core.state==MORI_FAULT);
 mori_trip(&r->core,MF_TIMING);CHECK(r->core.fault==fault);
}
static void fault_injections(void){
 static const struct {const char *name;mori_fault_t fault;} cases[]={
 {"IMU no response",MF_SENSOR},{"IMU old sample",MF_SENSOR},{"encoder jump",MF_ENCODER},
 {"ADC open",MF_SENSOR},{"ADC short",MF_SENSOR},{"NTC left open",MF_SENSOR},{"NTC right short",MF_SENSOR},
 {"signed bus overcurrent",MF_CURRENT},{"overtemperature",MF_TEMPERATURE},{"undervoltage",MF_LOW_VOLTAGE},
 {"overvoltage",MF_OVERVOLTAGE},{"nFAULT",MF_DRIVER},{"physical ESTOP",MF_ESTOP},{"control overrun",MF_TIMING},
 {"PWM submit overrun",MF_TIMING},{"nonfinite sensor",MF_SENSOR}};
 for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  sim_hal_t s;mori_runtime_t r;balance(&s,&r);
  switch(i){
   case 0:s.sample.imu_ok=false;break;case 1:s.imu_age=9000;break;case 2:s.counts[0]=1000;break;
   case 3:s.battery_raw=4095;break;case 4:s.battery_raw=0;break;
   case 5:s.ntc_raw[0]=4095;break;case 6:s.ntc_raw[1]=0;break;
   case 7:s.sample.bus_a=-1.4f;break;case 8:s.ntc_mv[0]=500;break;
   case 9:s.battery_mv=1475;break;case 10:s.battery_mv=2175;break;
   case 11:s.sample.driver_ok=false;break;case 12:s.sample.estop_ok=false;break;
   case 13:s.sample_cost=1801;break;case 14:s.apply_cost=1400;break;case 15:s.sample.ax=NAN;break;
  }
  sim_tick(&s,&r);assert_latched(&s,&r,cases[i].fault);
  /* A transient jump may have cleared; only an explicit ACK may recover. */
  printf("PASS injection: %s\n",cases[i].name);
 }
}
static void other_safety(void){
 sim_hal_t s;mori_runtime_t r;balance(&s,&r);
 command(&s,&r,"move .1 .05");for(int i=0;i<5;i++)sim_tick(&s,&r);
 command(&s,&r,"stop");CHECK(r.core.v_target==0&&r.core.yaw_target==0&&s.physical_output.enable);
 command(&s,&r,"move .1 0");for(int i=0;i<211;i++)sim_tick(&s,&r);
 CHECK(r.core.v_target==0&&r.core.state==MORI_BALANCE&&s.physical_output.enable);
 s.battery_mv=1675;sim_tick(&s,&r);CHECK(r.core.out.low_battery&&r.core.out.enable);
 s.battery_mv=1625;sim_tick(&s,&r);CHECK(r.core.out.request_support&&r.core.out.enable);
 balance(&s,&r);s.sample.estop_ok=false;sim_tick(&s,&r);s.sample.estop_ok=true;sim_tick(&s,&r);
 CHECK(r.core.state==MORI_FAULT);command(&s,&r,"ack");CHECK(r.core.state==MORI_DISARMED&&!r.core.calibrated&&!r.core.signs_confirmed);
 mori_request_t req;CHECK(mori_parse("arm balance",&req)==MR_OK);CHECK(mori_runtime_enqueue(&r,req));sim_tick(&s,&r);
 CHECK(!s.physical_output.enable);drain(&r);
 balance(&s,&r);mori_runtime_init(&r,(mori_config_t){0},false,false);sim_tick(&s,&r);CHECK(!s.physical_output.enable&&r.core.state==MORI_DISARMED);
 ready(&s,&r);command(&s,&r,"arm bench");uint64_t deadline=r.core.bench_deadline_us;
 for(int i=0;i<79;i++){command(&s,&r,"duty .12 -.12");CHECK(r.core.bench_deadline_us==deadline);CHECK(fabsf(s.physical_output.left)<=.12f);}
 while(s.frame_begin+2404<deadline)sim_tick(&s,&r);sim_tick(&s,&r);CHECK(!s.physical_output.enable);
 balance(&s,&r);for(int i=0;i<8;i++){CHECK(mori_parse("@1 stop",&req)==MR_OK);CHECK(mori_runtime_enqueue(&r,req));}
 CHECK(!mori_runtime_enqueue(&r,req));sim_tick(&s,&r);assert_latched(&s,&r,MF_QUEUE);drain(&r);
 balance(&s,&r);s.sample.gy=6;for(int i=0;i<35&&r.core.state!=MORI_FAULT;i++)sim_tick(&s,&r);assert_latched(&s,&r,MF_TILT);
 balance(&s,&r);r.core.cfg.kp=10;r.core.theta=.12f;
 for(int i=0;i<90;i++){s.counts[0]++;s.counts[1]--;s.sample.ax=-s.sample.az*tanf(.12f);sim_tick(&s,&r);}
 assert_latched(&s,&r,MF_SATURATION);
 balance(&s,&r);r.core.cfg.kp=4;r.core.theta=.12f;s.sample.ax=-s.sample.az*tanf(.12f);
 for(int i=0;i<90;i++)sim_tick(&s,&r);assert_latched(&s,&r,MF_ENCODER); /* frozen counters while driven */
 ready(&s,&r);command(&s,&r,"arm bench");s.battery_mv=1625;sim_tick(&s,&r);
 CHECK(r.core.out.low_battery&&r.core.out.request_support&&r.core.out.enable);
 /* Default gates cannot be bypassed by requests or test signs. */
 sim_hal_init(&s);mori_runtime_init(&r,(mori_config_t){0},false,false);sim_tick(&s,&r);
 const char *locked[]={"arm bench","arm balance","confirm_signs","head 0"};
 for(unsigned i=0;i<4;i++){CHECK(mori_parse(locked[i],&req)==MR_OK);CHECK(mori_runtime_enqueue(&r,req));sim_tick(&s,&r);mori_reply_t reply;CHECK(mori_runtime_reply(&r,&reply)&&reply.reason==MR_GATE);CHECK(!s.physical_output.enable&&!r.head_active);}
 /* A sudden correction is not slowed by the motion-target acceleration limit. */
 balance(&s,&r);r.core.theta=.1f;sim_tick(&s,&r);CHECK(s.physical_output.left>.09f);
}
static void protocol_tests(void){
 const char *bad[]={"duty .1 .1 trailing","head nan","move inf 0","move 1e999 0","move 1e-999 0","gains 1 .1 0","head 51","duty .12001 0","arm bench now","@4294967296 stop","@0 stop","stop x","head 0x1p0","head 1.2abc","head --1","gains 0 .1 0 0","move .1\t.1","@1","head","head -Inf"};
 mori_request_t req;
 for(unsigned i=0;i<sizeof(bad)/sizeof(bad[0]);i++)CHECK(mori_parse(bad[i],&req)!=MR_OK);
 const char *good[]={"@1 info","@4294967295 stop","head -5e1","duty -.12 .12","move -.3 .1","gains 1 .1 0 0","disarm","status"};
 for(unsigned i=0;i<sizeof(good)/sizeof(good[0]);i++)CHECK(mori_parse(good[i],&req)==MR_OK);
 mori_line_t line={0};mori_reason_t why;char bytes[160];memset(bytes,'x',sizeof(bytes));
 for(unsigned i=0;i<sizeof(bytes);i++)CHECK(!mori_line_feed(&line,(uint8_t)bytes[i],10+i,&req,&why));
 CHECK(mori_line_feed(&line,'\n',1000,&req,&why)&&why==MR_OVERFLOW);
 CHECK(!mori_line_feed(&line,'\r',1001,&req,&why));
 const char *partial="@99 arm";for(size_t i=0;i<strlen(partial);i++)mori_line_feed(&line,partial[i],100+i,&req,&why);
 CHECK(mori_line_expire(&line,300000,&why)&&why==MR_TRUNCATED);
 const char *suffix=" bench\n";for(size_t i=0;i<strlen(suffix);i++)CHECK(!mori_line_feed(&line,suffix[i],300001+i,&req,&why));
 mori_line_feed(&line,'s',1,&req,&why);mori_line_feed(&line,0,2,&req,&why);
 CHECK(mori_line_feed(&line,'\n',3,&req,&why)&&why==MR_SYNTAX);
}
static void transforms_and_ui(void){
 mori_mount_t m={.rotation={{0,-1,0},{1,0,0},{0,0,1}},.encoder_sign={1,-1},.motor_sign={1,-1}};
 CHECK(mori_mount_valid(&m));float raw[3]={0,-9.80665f,0},out[3];mori_rotate(&m,raw,out);CHECK(fabsf(out[0]-9.80665f)<1e-5);
 m.rotation[2][2]=-1;CHECK(!mori_mount_valid(&m));m.rotation[2][2]=NAN;CHECK(!mori_mount_valid(&m));
 CHECK(fabs(MORI_WHEEL_M_PER_COUNT-3.141592653589793*.095/979.616)<1e-10);
 CHECK(fabsf(mori_shunt_current(0xff,0x9c)+.01f)<1e-6f);
 float t;CHECK(mori_ntc(1.65f,&t)&&fabsf(t-25)<.01f);CHECK(!mori_ntc(3.3f,&t));CHECK(!mori_ntc(0,&t));
 mori_encoder_t encoder={0};int signs[2]={1,1};float speed[2];int32_t count[2]={0};
 for(int i=0;i<8;i++){count[0]=(i==0?1:1);CHECK(mori_encoder_update(&encoder,count,.002404f,signs,speed));}
 CHECK(fabs(speed[0]-MORI_WHEEL_M_PER_COUNT/(8*.002404f))<1e-6);
 mori_head_guard_t guard={0};
 CHECK(mori_head_guard(&guard,1,true,true,.02f));CHECK(!mori_head_guard(&guard,1,true,false,.02f));
 CHECK(!mori_head_guard(&guard,1,true,true,.02f));CHECK(mori_head_guard(&guard,2,true,true,.02f));
 CHECK(!mori_head_guard(&guard,2,true,true,.2f));CHECK(!mori_head_guard(&guard,2,true,true,.02f));
 mori_head_trajectory_t h={0};float previous_v=0;
 for(int i=0;i<400;i++){mori_head_step(&h,40,.02f);CHECK(fabsf(h.velocity-previous_v)<=1.20001f);CHECK(fabsf(h.position)<=50);previous_v=h.velocity;}
 CHECK(fabsf(h.position-40)<.1f);CHECK(fabsf(mori_head_pulse_us(10)-1370.37037f)<.01f);CHECK(isnan(mori_head_pulse_us(60)));
 unsigned sizes[]={64,240,360};for(unsigned i=0;i<3;i++){CHECK(mori_face_pixel(sizes[i],sizes[i],0,0,false,false)==0);CHECK(mori_face_pixel(sizes[i],sizes[i],sizes[i]*35/100,sizes[i]*43/100,false,false)!=0);}
 uint32_t hist[33]={0};hist[0]=50;hist[1]=45;hist[32]=5;CHECK(mori_hist_quantile_upper(hist,50)==100);CHECK(mori_hist_quantile_upper(hist,95)==200);CHECK(mori_hist_quantile_upper(hist,99)==UINT32_MAX);
}
int main(void){protocol_tests();transforms_and_ui();fault_injections();other_safety();printf("PASS %u assertions; SIMULATED HAL, virtual clock, no hardware evidence\n",checks);return 0;}
