#include "mori12.h"
#include "timing.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
static unsigned checks;
#define CHECK(x) do { checks++; if(!(x)){fprintf(stderr,"check %u failed %s:%d: %s\n",checks,__FILE__,__LINE__,#x);assert(x);} } while(0)
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));}
static void feedback_packet(uint8_t b[26]){
 memset(b,0,26);b[0]=0xfc;b[1]=0xee;b[2]=0x90;b[3]=250;b[4]=200;b[5]=24;
 b[6]=0x00;b[7]=0xff;b[8]=128;put32(b+10,32768);b[18]=0;b[19]=16;
 uint32_t crc;CHECK(s288_crc(b+2,20,&crc));put32(b+22,crc);
}
static void protocols(void){
 uint8_t b[26],tx[20];s288_feedback f={0};feedback_packet(b);
 CHECK(s288_decode(b,26,0,&f));CHECK(f.temperature_c==-6&&f.sensor==200&&f.voltage_v==12&&f.timeout_active);
 CHECK(f.torque_raw==-256&&fabs(f.torque_estimate_nm+S288_RATIO/1000)<1e-9);
 CHECK(fabs(f.position_rad-6.283185307179586/S288_RATIO)<1e-12);CHECK(fabs(f.absolute_output_rad-3.141592653589793)<1e-12);
 for(size_t n=0;n<26;n++){CHECK(!s288_decode(b,n,0,&f));}
 CHECK(!s288_decode(b,27,0,&f));CHECK(!s288_decode(b,26,1,&f));
 for(unsigned i=0;i<26;i++)for(unsigned j=0;j<8;j++){b[i]^=(uint8_t)(1u<<j);CHECK(!s288_decode(b,26,0,&f));b[i]^=(uint8_t)(1u<<j);}
 s288_stream stream={0};unsigned frames=0;uint8_t garbage[]={0,0xfc,0xfc,0xee,0,0};
 for(unsigned i=0;i<sizeof(garbage);i++)frames+=s288_feed(&stream,garbage[i],0,&f);
 for(unsigned i=0;i<26;i++){frames+=s288_feed(&stream,b[i],0,&f);}
 CHECK(frames==1&&stream.discarded>0);
 s288_command c={.id=0,.mode=1,.timeout=true,.torque_nm=.01,.speed_rad_s=1,.position_rad=.1};
 CHECK(s288_encode(&c,tx));CHECK(tx[0]==0xfe&&tx[1]==0xee&&tx[2]==0x90);c.torque_nm=NAN;CHECK(!s288_encode(&c,tx));c.torque_nm=INFINITY;CHECK(!s288_encode(&c,tx));c.torque_nm=1e30;CHECK(!s288_encode(&c,tx));c.torque_nm=0;c.id=15;CHECK(!s288_encode(&c,tx));c.id=0;c.mode=2;CHECK(!s288_encode(&c,tx));
 c.mode=1;c.kp=40000.*S288_RATIO*S288_RATIO/1280000.;CHECK(!s288_encode(&c,tx));c.kp=0;c.kd=40000.*S288_RATIO*S288_RATIO/128000000.;CHECK(!s288_encode(&c,tx));
 uint32_t crc;CHECK(!s288_crc(b,25,&crc));
 mori_wheel_cal cal={-1,1,1,.0475,.1,false};double speed;CHECK(!mori_wheel_velocity(&f,&cal,&speed));cal.verified=true;f.timeout_active=false;f.speed_rad_s=6.283185307179586;CHECK(mori_wheel_velocity(&f,&cal,&speed));CHECK(fabs(speed+3.141592653589793*.095)<1e-9);cal.servo_turns_per_wheel_turn=2;CHECK(mori_wheel_velocity(&f,&cal,&speed)&&fabs(speed+3.141592653589793*.095/2)<1e-9);cal.output_sign=-1;CHECK(mori_wheel_torque_packet(0,.05,&cal,tx)&&tx[5]==255);CHECK(!mori_wheel_torque_packet(0,.2,&cal,tx));
 s288_position pos={0};CHECK(s288_unwrap(&pos,INT32_MAX-2,100,100,20));CHECK(s288_unwrap(&pos,INT32_MIN+2,110,100,20));CHECK(pos.accumulated==(int64_t)INT32_MAX+3);CHECK(!s288_unwrap(&pos,1000,120,100,20));CHECK(!s288_unwrap(&pos,INT32_MIN+3,1000,100,20));
 uint16_t brr;double baud;CHECK(mori_uart_divider(48000000,6000000,1000,&brr,&baud));CHECK(brr==0x10&&baud==6000000);CHECK(!mori_uart_divider(50000000,6000000,1000,&brr,&baud));CHECK(!mori_uart_divider(16000000,6000000,1000,&brr,&baud));
 mori_bus bus={0};CHECK(mori_bus_start(&bus,1000,200));CHECK(bus.tx_enable);mori_bus_dma_done(&bus);CHECK(bus.tx_enable&&bus.phase==BUS_WAIT_TC);CHECK(!mori_bus_reply(&bus,0,1010));mori_bus_tc(&bus);CHECK(!bus.tx_enable);CHECK(mori_bus_reply(&bus,0,1100));CHECK(bus.wheel==1);CHECK(mori_bus_start(&bus,1100,200));CHECK(mori_bus_poll(&bus,1300));CHECK(bus.timeouts[1]==1&&bus.wheel==0);CHECK(!mori_bus_fresh(&bus,1300,1000,500));
 CHECK(mori_bus_start(&bus,1300,200));mori_bus_dma_done(&bus);mori_bus_tc(&bus);CHECK(mori_bus_reply(&bus,0,1400));CHECK(mori_bus_start(&bus,1400,200));mori_bus_dma_done(&bus);mori_bus_tc(&bus);CHECK(mori_bus_reply(&bus,1,1500));CHECK(mori_bus_fresh(&bus,1600,1000,500));CHECK(!mori_bus_fresh(&bus,2600,1000,500));CHECK(!mori_bus_fresh(&bus,1600,1000,50));
}
static bool region(double yaw,double pitch,void *ctx){(void)ctx;return fabs(yaw)+2*fabs(pitch)<=1;}
static void sensors(void){
 uint8_t tx[13];CHECK(scs_read_feedback(1,tx)==8&&tx[5]==56&&tx[6]==8);CHECK(scs_read_feedback(254,tx)==0);
 CHECK(scs_write_position(1,512,100,20,tx));CHECK(tx[6]==2&&tx[7]==0);CHECK(!scs_write_position(1,1024,100,20,tx));
 uint8_t fb[14]={255,255,1,10,0,2,0,0x80,2,4,3,60,35,0};unsigned sum=0;for(unsigned i=2;i<13;i++)sum+=fb[i];fb[13]=(uint8_t)~sum;
 scs_feedback f;CHECK(scs_decode_feedback(fb,14,1,&f));CHECK(f.position_raw==512&&f.speed_raw==-2&&f.load_raw==-3&&f.voltage_raw==60);fb[13]^=1;CHECK(!scs_decode_feedback(fb,14,1,&f));
 double angle; mori_joint_cal cal={512,.005,-1,1,-1,false};CHECK(!scs_joint_angle(&f,&cal,&angle));cal.verified=true;f.position_raw=522;CHECK(scs_joint_angle(&f,&cal,&angle)&&fabs(angle+.05)<1e-12);
 mori_head head={0};double target[2]={.2,.1};double prior_v=0;
 for(unsigned i=0;i<1000;i++){if(i==100)target[0]=-.1;CHECK(mori_head_step(&head,target,.01,.3,.5,region,NULL,false));CHECK(fabs(head.velocity[0]-prior_v)<=.00500001);prior_v=head.velocity[0];}
 CHECK(fabs(head.angle[0]+.1)<1e-5&&fabs(head.velocity[0])<1e-5);
 target[0]=.9;target[1]=.2;CHECK(!mori_head_step(&head,target,.01,.3,.5,region,NULL,false));target[0]=NAN;CHECK(!mori_head_step(&head,target,.01,.3,.5,region,NULL,false));
 const double r[9]={1,0,0,0,1,0,0,0,1},mirror[9]={-1,0,0,0,1,0,0,0,1};CHECK(mori_rotation_valid(r));CHECK(!mori_rotation_valid(mirror));CHECK(icm42688_identity(0x47));CHECK(!icm42688_identity(0x6c));
 uint8_t burst[14]={0};burst[6]=0x40;burst[10]=0x40;mori_imu imu;CHECK(icm42688_decode(burst,14,2,500,r,123,&imu));CHECK(fabs(imu.accel_m_s2[2]-9.80665)<1e-6);CHECK(fabs(imu.gyro_rad_s[1]-250*3.141592653589793/180)<1e-6);CHECK(imu.sampled_us==123);CHECK(!icm42688_decode(burst,13,2,500,r,123,&imu));burst[2]=128;CHECK(!icm42688_decode(burst,14,2,500,r,123,&imu));
}
/* These are test-fixture values, NOT robot gains or physical authorization. */
static mori_parameters fixture(void){return (mori_parameters){true,true,true,.0475,.1,1,.1,.1,.01,.08,.35,3000,3000,2000,5000,10000,1};}
static mori_sample fresh(uint64_t t){return (mori_sample){.imu_us=t,.wheel_us={t,t},.imu_valid=true,.wheel_valid={true,true},.power_ok=true,.estop_ok=true,.head_valid=true};}
static void ready(mori_motion *m,uint64_t t){mori_motion_init(m);mori_parameters p=fixture();CHECK(mori_motion_configure(m,&p,true));mori_sample s=fresh(t);CHECK(mori_motion_arm(m,&s,t,true));}
static void safety(void){
 mori_motion m;mori_motion_init(&m);mori_sample s=fresh(1000);CHECK(!m.drive_requested&&m.external_inhibit_requested);CHECK(!mori_motion_arm(&m,&s,1000,true));
 mori_parameters p=fixture();p.kp_pitch=NAN;CHECK(!mori_motion_configure(&m,&p,true));p=fixture();CHECK(!mori_motion_configure(&m,&p,false));p.physical_verified=false;CHECK(!mori_motion_configure(&m,&p,true));
 ready(&m,1000);s.pitch_rad=.05;mori_motion_step(&m,&s,1000);CHECK(m.left_nm>0&&m.right_nm>0&&m.healthy_frames==1);CHECK(!mori_motion_target(&m,NAN,0,1000,300000));CHECK(!mori_motion_target(&m,.11,0,1000,300000));CHECK(mori_motion_target(&m,.1,.1,1000,300000));
 s=fresh(3000);s.pitch_rad=.09;mori_motion_step(&m,&s,3000);CHECK(fabs(m.left_nm)<=.1&&fabs(m.right_nm)<=.1);CHECK(m.limited_v<=.0004);mori_motion_stop(&m);CHECK(m.drive_requested&&m.state==M_ARMED_IDLE&&m.target_v==0);CHECK(!mori_motion_disarm(&m,false));CHECK(mori_motion_disarm(&m,true)&&!m.drive_requested);
 ready(&m,1000);CHECK(mori_motion_target(&m,.05,0,1000,1000));s=fresh(3000);mori_motion_step(&m,&s,3000);CHECK(m.target_v==0&&m.drive_requested);
 ready(&m,1000);s=fresh(1000);s.low_battery=true;mori_motion_step(&m,&s,1000);CHECK(m.drive_requested&&m.head_inhibited&&m.target_v==0);mori_motion_disarm(&m,true);CHECK(!mori_motion_arm(&m,&s,1000,true));
 for(unsigned scenario=0;scenario<9;scenario++){
  ready(&m,10000);s=fresh(10000);mori_fault expected=F_NONE;
  switch(scenario){case 0:s.imu_valid=false;expected=F_IMU;break;case 1:s.imu_us=6000;expected=F_IMU;break;case 2:s.wheel_valid[0]=false;expected=F_WHEEL;break;case 3:s.wheel_us[1]=7000;expected=F_WHEEL;break;case 4:s.pitch_rad=.5;expected=F_TILT;break;case 5:s.power_ok=false;expected=F_POWER;break;case 6:s.estop_ok=false;expected=F_ESTOP;break;case 7:s.pitch_rad=NAN;expected=F_INPUT;break;case 8:s.imu_us=10001;expected=F_IMU;break;}
  mori_motion_step(&m,&s,10000);CHECK(m.fault==expected&&!m.drive_requested&&m.external_inhibit_requested&&m.left_nm==0);s=fresh(11000);mori_motion_step(&m,&s,11000);CHECK(m.state==M_FAULT);CHECK(!mori_motion_arm(&m,&s,11000,true));CHECK(!mori_motion_ack(&m,true,false));CHECK(mori_motion_ack(&m,true,true));CHECK(!m.drive_requested&&m.state==M_DISARMED);
 }
 ready(&m,1000);s=fresh(1000);mori_motion_step(&m,&s,1000);s=fresh(7000);mori_motion_step(&m,&s,7000);CHECK(m.fault==F_CONTROL_TIMEOUT);
 ready(&m,1000);for(uint64_t t=1000;t<=13000;t+=2000){s=fresh(t);s.pitch_rad=.2;mori_motion_step(&m,&s,t);}CHECK(m.fault==F_SATURATION&&!m.drive_requested);
 ready(&m,1000);mori_motion_fault(&m,F_QUEUE);CHECK(m.fault==F_QUEUE&&!m.drive_requested);mori_motion_init(&m);CHECK(m.state==M_DISARMED&&!m.drive_requested&&m.parameters.kp_pitch==0);
 ready(&m,1000);m.state=M_AUTONOMY;s=fresh(1000);s.head_valid=false;mori_motion_step(&m,&s,1000);CHECK(m.head_inhibited&&m.target_v==0&&m.drive_requested);
}
static void timings(void){mori_timing t={0};for(int i=0;i<T_STAGES;i++)CHECK(mori_timing_mark(&t,(enum mori_timing_stage)i,1000+i*100));CHECK(t.frames==1&&t.execution_max_us==400&&t.max_us[0]==100);CHECK(!mori_timing_mark(&t,T_CONTROL_DONE,2000));CHECK(t.invalid_frames==1);CHECK(mori_timing_mark(&t,T_DRDY,3000));CHECK(t.period_max_us==2000);uint16_t brr;double baud;CHECK(mori_uart_divider(96000000,6000000,1000,&brr,&baud)&&brr==0x20&&baud==6000000);}
int main(void){protocols();sensors();safety();timings();printf("MORI V1.2 HOST_TEST PASS: %u assertions; simulated HAL/time; BENCH/ROBOT NOT_TESTED\n",checks);return 0;}
