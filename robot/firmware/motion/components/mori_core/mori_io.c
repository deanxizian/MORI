#include "mori_io.h"
#include <math.h>
#include <stddef.h>
#include <stdlib.h>

bool mori_mount_valid(const mori_mount_t *m){
 for(int i=0;i<2;i++)if((m->encoder_sign[i]!=1&&m->encoder_sign[i]!=-1)||(m->motor_sign[i]!=1&&m->motor_sign[i]!=-1))return false;
 for(int i=0;i<3;i++)for(int j=0;j<3;j++){
  float dot=0;for(int k=0;k<3;k++){if(!isfinite(m->rotation[i][k]))return false;dot+=m->rotation[i][k]*m->rotation[j][k];}
  if(fabsf(dot-(i==j?1.0f:0.0f))>1e-4f)return false;
 }
 const float (*r)[3]=m->rotation;
 float det=r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])-r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])+r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0]);
 return fabsf(det-1)<1e-4f; /* right-handed proper rotation, never a reflection */
}
void mori_rotate(const mori_mount_t *m,const float raw[3],float out[3]){
 for(int i=0;i<3;i++){out[i]=0;for(int j=0;j<3;j++)out[i]+=m->rotation[i][j]*raw[j];}
}
bool mori_adc_voltage(int raw,int mv,float *v){
 if(raw<10||raw>4080||mv<=0||mv>=3300)return false;
 *v=mv*.001f;return true;
}
bool mori_ntc(float v,float *t){
 if(!isfinite(v)||v<.08f||v>3.05f)return false;
 float r=10000*v/(3.3f-v);*t=1/(1/298.15f+logf(r/10000)/3380)-273.15f;
 return isfinite(*t);
}
float mori_shunt_current(uint8_t hi,uint8_t lo){
 int32_t raw=((uint32_t)hi<<8)|lo;if(raw>=32768)raw-=65536;
 return raw*.0001f; /* signed shunt 10uV / 0.1ohm; not phase current */
}
bool mori_encoder_update(mori_encoder_t *e,const int32_t counts[2],float dt,const int signs[2],float speed[2]){
 bool ok=isfinite(dt)&&dt>0&&dt<.02f;
 for(int i=0;i<2;i++){
  uint32_t u=(uint32_t)counts[i]-e->last[i];e->last[i]=(uint32_t)counts[i];
  int64_t d=u<=INT32_MAX?(int64_t)u:(int64_t)u-4294967296LL;
  if(d>80||d< -80||abs(signs[i])!=1)ok=false;
  e->delta[i][e->index]=(d>80||d< -80)?0:(int32_t)d;
 }
 if(!ok){speed[0]=speed[1]=0;return false;}
 e->elapsed[e->index]=dt;e->index=(e->index+1)%8;if(e->count<8)e->count++;
 float elapsed=0;int sum[2]={0};
 for(unsigned k=0;k<e->count;k++){elapsed+=e->elapsed[k];for(int i=0;i<2;i++)sum[i]+=e->delta[i][k];}
 /* Keep realtime arithmetic in float; INFO retains the exact constant's precision. */
 const float metres_per_count=(float)MORI_WHEEL_M_PER_COUNT;
 for(int i=0;i<2;i++)speed[i]=sum[i]*metres_per_count/elapsed*signs[i];
 return true;
}
