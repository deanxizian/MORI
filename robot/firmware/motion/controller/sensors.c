#include "mori12.h"
#include <math.h>
#include <string.h>
static uint16_t be16(const uint8_t *p){return (uint16_t)((uint16_t)p[0]<<8|p[1]);}
static int signed16(const uint8_t *p){uint16_t u=be16(p);return u<=32767?(int)u:(int)u-65536;}
static uint8_t checksum(const uint8_t *p,size_t n){unsigned sum=0;for(size_t i=2;i<n-1;i++)sum+=p[i];return (uint8_t)~sum;}
size_t scs_read_feedback(uint8_t id,uint8_t out[8]){
 if(id>253||!out)return 0;
 const uint8_t b[8]={255,255,id,4,2,56,8,0};memcpy(out,b,8);out[7]=checksum(out,8);return 8;
}
bool scs_write_position(uint8_t id,uint16_t pos,uint16_t time,uint16_t speed,uint8_t out[13]){
 if(id>253||pos>1023||!out)return false;
 uint8_t b[13]={255,255,id,9,3,42,(uint8_t)(pos>>8),(uint8_t)pos,(uint8_t)(time>>8),(uint8_t)time,(uint8_t)(speed>>8),(uint8_t)speed,0};
 b[12]=checksum(b,13);memcpy(out,b,13);return true;
}
bool scs_decode_feedback(const uint8_t *p,size_t n,uint8_t id,scs_feedback *out){
 if(!p||!out||n!=14||id>253||p[0]!=255||p[1]!=255||p[2]!=id||p[3]!=10||checksum(p,n)!=p[13]||be16(p+5)>1023)return false;
 scs_feedback f={0};f.id=id;f.error=p[4];f.position_raw=be16(p+5);unsigned speed=be16(p+7),load=be16(p+9);
 if(load&~2047u)return false;
 f.speed_raw=speed&32768?-(int)(speed&32767):(int)speed;f.load_raw=load&1024?-(int)(load&1023):(int)load;
 f.voltage_raw=p[11];f.temperature_c=p[12];*out=f;return true;
}
bool scs_joint_angle(const scs_feedback *f,const mori_joint_cal *c,double *out){
 if(!f||!c||!out||!c->verified||f->error||f->position_raw>1023||(c->sign!=1&&c->sign!=-1)||!isfinite(c->zero_raw)||!isfinite(c->rad_per_count)||c->rad_per_count<=0||!isfinite(c->min_rad)||!isfinite(c->max_rad)||c->min_rad>=c->max_rad)return false;
 double a=(f->position_raw-c->zero_raw)*c->rad_per_count*c->sign;if(a<c->min_rad||a>c->max_rad)return false;*out=a;return true;
}
bool mori_head_step(mori_head *h,const double target[2],double dt,double speed,double accel,mori_head_region region,void *ctx,bool inhibit){
 if(!h||!target||!region||!isfinite(dt)||dt<=0||dt>.1||!isfinite(speed)||speed<=0||!isfinite(accel)||accel<=0)return false;
 for(unsigned i=0;i<2;i++)if(!isfinite(target[i])||!isfinite(h->angle[i])||!isfinite(h->velocity[i]))return false;
 if(!region(target[0],target[1],ctx))return false;
 if(inhibit){h->velocity[0]=h->velocity[1]=0;return true;}
 mori_head next=*h;
 for(unsigned i=0;i<2;i++){
  double error=target[i]-h->angle[i];
  /* Reserve the next discrete step as well as the continuous stopping distance.
   * On retarget, braking may cross the target; never teleport velocity to zero. */
  double braking=sqrt(2*accel*fabs(error)+accel*accel*dt*dt)-accel*dt;
  double v=copysign(fmin(speed,braking),error);
  next.velocity[i]=fmax(h->velocity[i]-accel*dt,fmin(h->velocity[i]+accel*dt,v));
  double delta=next.velocity[i]*dt;
  if(fabs(delta)>=fabs(error)&&delta*error>=0&&fabs(h->velocity[i])<=accel*dt){next.angle[i]=target[i];next.velocity[i]=0;}
  else next.angle[i]+=delta;
 }
 if(!region(next.angle[0],next.angle[1],ctx)){h->velocity[0]=h->velocity[1]=0;return false;}
 *h=next;return true;
}
bool icm42688_identity(uint8_t id){return id==0x47;}
bool mori_rotation_valid(const double r[9]){
 if(!r)return false;
 for(unsigned i=0;i<9;i++)if(!isfinite(r[i]))return false;
 for(unsigned a=0;a<3;a++)for(unsigned b=0;b<3;b++){double dot=0;for(unsigned j=0;j<3;j++)dot+=r[a*3+j]*r[b*3+j];if(fabs(dot-(a==b?1:0))>1e-6)return false;}
 double det=r[0]*(r[4]*r[8]-r[5]*r[7])-r[1]*(r[3]*r[8]-r[5]*r[6])+r[2]*(r[3]*r[7]-r[4]*r[6]);return fabs(det-1)<1e-6;
}
bool icm42688_decode(const uint8_t *b,size_t n,double ar,double gr,const double r[9],uint64_t time,mori_imu *out){
 if(!b||!out||n!=14||!mori_rotation_valid(r)||(ar!=2&&ar!=4&&ar!=8&&ar!=16)||(gr!=15.625&&gr!=31.25&&gr!=62.5&&gr!=125&&gr!=250&&gr!=500&&gr!=1000&&gr!=2000))return false;
 mori_imu f={0};f.temperature_c=signed16(b)/132.48+25;f.sampled_us=time;
 for(unsigned j=0;j<3;j++){
  int a=signed16(b+2+2*j),g=signed16(b+8+2*j);if(a==-32768||g==-32768)return false; /* datasheet invalid sample sentinel */
  for(unsigned i=0;i<3;i++){f.accel_m_s2[i]+=r[i*3+j]*a*ar*9.80665/32768;f.gyro_rad_s[i]+=r[i*3+j]*g*gr*0.017453292519943295/32768;}
 }
 f.valid=true;*out=f;return true;
}
