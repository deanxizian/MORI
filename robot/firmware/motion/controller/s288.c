/* Protocol independently serialized against Unitree digital_servo 75c1ed6.
 * See software/THIRD_PARTY_V1_2.md for the upstream non-commercial restriction.
 * No packed struct or hardware capture is used as evidence. */
#include "mori12.h"
#include <math.h>
#include <string.h>
#include <limits.h>
#define TAU 6.28318530717958647693
static uint16_t u16(const uint8_t *p) { return (uint16_t)(p[0] | (uint16_t)p[1]<<8); }
static uint32_t u32(const uint8_t *p) { return p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24; }
static int16_t i16(const uint8_t *p) { uint16_t u=u16(p); return (int16_t)(u<=INT16_MAX?(int32_t)u:(int32_t)u-65536); }
static int32_t i32(const uint8_t *p) { uint32_t u=u32(p); return (int32_t)(u<=INT32_MAX?(int64_t)u:(int64_t)u-4294967296LL); }
static void put16(uint8_t *p,uint16_t n) { p[0]=(uint8_t)n;p[1]=(uint8_t)(n>>8); }
static void put32(uint8_t *p,uint32_t n) { for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i)); }
bool s288_crc(const uint8_t *p,size_t n,uint32_t *out) {
 if(!p||!out||n%4)return false;
 uint32_t c=UINT32_MAX;
 for(size_t j=0;j<n;j+=4){c^=u32(p+j);for(unsigned b=0;b<32;b++)c=(c<<1)^((c&0x80000000u)?0x04c11db7u:0);}
 *out=c;return true;
}
bool s288_encode(const s288_command *c,uint8_t out[20]) {
 if(!c||!out||c->id>14||c->mode>1)return false;
 double t=c->torque_nm/S288_RATIO*256000.,v=c->speed_rad_s*S288_RATIO*2.56/TAU;
 double p=c->position_rad*S288_RATIO*32768./TAU,kp=c->kp/(S288_RATIO*S288_RATIO)*1280000.;
 double kd=c->kd/(S288_RATIO*S288_RATIO)*128000000.;
 if(!isfinite(t)||!isfinite(v)||!isfinite(p)||!isfinite(kp)||!isfinite(kd)||t<INT16_MIN||t>INT16_MAX||v<INT16_MIN||v>INT16_MAX||p<INT32_MIN||p>INT32_MAX||kp<0||kp>INT16_MAX||kd<0||kd>INT16_MAX)return false;
 uint8_t b[20]={0xfe,0xee,(uint8_t)(c->id|(c->mode<<4)|(c->timeout?0x80:0)),0};
 put16(b+4,(uint16_t)(int16_t)t);put16(b+6,(uint16_t)(int16_t)v);put32(b+8,(uint32_t)(int32_t)p);
 put16(b+12,(uint16_t)kp);put16(b+14,(uint16_t)kd);uint32_t crc;s288_crc(b,16,&crc);put32(b+16,crc);
 memcpy(out,b,20);return true;
}
bool s288_decode(const uint8_t *p,size_t n,uint8_t id,s288_feedback *out) {
 uint32_t crc;if(!p||!out||n!=26||id>14||p[0]!=0xfc||p[1]!=0xee||(p[2]&15)!=id||((p[2]>>4)&7)>1)return false;
 if(!s288_crc(p+2,20,&crc)||crc!=u32(p+22))return false;
 s288_feedback f={0};f.id=id;f.mode=(p[2]>>4)&7;f.temperature_c=(int8_t)(p[3]<128?p[3]:(int)p[3]-256);
 f.timeout_active=(p[2]&128)!=0;f.sensor=p[4];f.voltage_raw=p[5];f.torque_raw=i16(p+6);f.speed_raw=i16(p+8);f.rotor_position_raw=i32(p+10);f.errors=u32(p+14);
 f.output_position_raw=u16(p+18)&8191;f.warning=(uint8_t)(u16(p+18)>>13);f.voltage_v=f.voltage_raw/2.;
 f.torque_estimate_nm=f.torque_raw/256000.*S288_RATIO;f.speed_rad_s=f.speed_raw/2.56*TAU/S288_RATIO;
 f.position_rad=f.rotor_position_raw/32768.*TAU/S288_RATIO;f.absolute_output_rad=f.output_position_raw/8192.*TAU;
 *out=f;return true;
}
bool s288_feed(s288_stream *s,uint8_t b,uint8_t id,s288_feedback *out) {
 if(!s||!out)return false;
 if(s->used>=26)s->used=0;
 s->bytes[s->used++]=b;
 while(s->used && (s->bytes[0]!=0xfc || (s->used>1&&s->bytes[1]!=0xee))){memmove(s->bytes,s->bytes+1,--s->used);s->discarded++;}
 if(s->used<26)return false;
 if(s288_decode(s->bytes,26,id,out)){s->used=0;return true;}
 s->bad_frames++;memmove(s->bytes,s->bytes+1,25);s->used=25;return false;
}
bool s288_unwrap(s288_position *s,int32_t raw,uint64_t now,uint64_t max_gap,uint32_t max_delta) {
 if(!s||!max_gap||!max_delta||max_delta>INT32_MAX)return false;
 if(!s->valid){s->valid=true;s->last=raw;s->accumulated=raw;s->sampled_us=now;return true;}
 if(now<=s->sampled_us||now-s->sampled_us>max_gap)return false;
 uint32_t delta=(uint32_t)raw-(uint32_t)s->last;int64_t d=delta<=INT32_MAX?(int64_t)delta:(int64_t)delta-4294967296LL;
 if(d>(int64_t)max_delta||d<-(int64_t)max_delta|| (d>0&&s->accumulated>INT64_MAX-d)||(d<0&&s->accumulated<INT64_MIN-d))return false;
 s->accumulated+=d;s->last=raw;s->sampled_us=now;return true;
}
bool mori_uart_divider(uint32_t clock,uint32_t baud,uint32_t max_ppm,uint16_t *brr,double *actual) {
 if(!baud||!clock||!brr||!actual)return false;
 /* STM32F4 OVER8: BRR fractional bit3 must be zero. */
 uint64_t divider=((uint64_t)clock+baud/2)/baud;
 if(divider<8||divider>32767)return false;
 double rate=(double)clock/(double)divider;
 if(fabs(rate-baud)/baud*1e6>max_ppm)return false;
 *brr=(uint16_t)(((divider/8)<<4)|(divider%8));*actual=rate;return true;
}
static bool wheel_cal_valid(const mori_wheel_cal *c){
 return c&&c->verified&&(c->encoder_sign==1||c->encoder_sign==-1)&&(c->output_sign==1||c->output_sign==-1)&&isfinite(c->servo_turns_per_wheel_turn)&&c->servo_turns_per_wheel_turn>0&&isfinite(c->wheel_radius_m)&&c->wheel_radius_m>0&&isfinite(c->allowed_servo_torque_nm)&&c->allowed_servo_torque_nm>0;
}
bool mori_wheel_velocity(const s288_feedback *f,const mori_wheel_cal *c,double *speed){
 if(!f||!speed||!wheel_cal_valid(c)||f->errors||f->timeout_active||!isfinite(f->speed_rad_s))return false;
 double value=f->speed_rad_s/c->servo_turns_per_wheel_turn*c->wheel_radius_m*c->encoder_sign;
 if(!isfinite(value))return false;
 *speed=value;return true;
}
bool mori_wheel_torque_packet(uint8_t id,double torque,const mori_wheel_cal *c,uint8_t packet[20]){
 if(!wheel_cal_valid(c)||!isfinite(torque)||fabs(torque)>c->allowed_servo_torque_nm)return false;
 s288_command command={.id=id,.mode=1,.timeout=true,.torque_nm=torque*c->output_sign};return s288_encode(&command,packet);
}
