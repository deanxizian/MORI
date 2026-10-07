/* Eyes-only projection/liveliness adapted from bloub face.ts/math.ts, MIT.
 * Copyright (c) 2026 Jérémy Perret; full license in THIRD_PARTY_NOTICES.
 * MORI states, interruptible interpolation and pixel clipping are new. */
#include "eyes.h"
#include <math.h>
#include <stddef.h>
static float limit(float x,float a,float b){return fminf(b,fmaxf(a,x));}
static float noise(float t,float p,float s){float x=t/p*6.28318530718f;return .55f*sinf(x+s)+.3f*sinf(2*x+s*1.7f+1.1f)+.15f*sinf(3*x+s*2.3f+2.4f);}
static float rng(uint32_t *a){*a+=0x6d2b79f5u;uint32_t t=(*a^(*a>>15))*(1|*a);t^=t+(t^(t>>7))*(61|t);return (double)(t^(t>>14))/4294967296.0;}
static float blink(float t){uint32_t seed=0x5eed;float start=1.4f;while(start<900){float k=(t-start)/.18f;if(t<start)break;if(k>=0&&k<=1)return k<.45f?1-k/.45f:(k-.45f)/.55f;start+=1.9f+rng(&seed)*2.7f;if(rng(&seed)<.18f){k=(t-start)/.18f;if(k>=0&&k<=1)return k<.45f?1-k/.45f:(k-.45f)/.55f;start+=.24f;}}return 1;}
static void spin(float u[3],float v[3],float degrees){float c=cosf(degrees*.01745329252f),s=sinf(degrees*.01745329252f);for(int i=0;i<3;i++){float a=u[i],b=v[i];u[i]=a*c+b*s;v[i]=b*c-a*s;}}
static void target(int state,float t,float rms,mori_eye_t out[2]){
 static const float p[8][5]={{0,0,0,1,1},{0,5,0,1,1.15},{12,8,-5,.92,.8},{0,2,0,1,1},{0,4,0,1.05,.55},{-9,2,10,1,.85},{0,0,0,1,.06},{0,0,0,1,.45}};
 float wander=state==6?0:.35f;
 float yaw=p[state][0]+(noise(t,11.3f,.4f)*5.5f+noise(t,3.7f,2.1f)*1.6f)*wander;
 float pitch=p[state][1]+(noise(t,9.1f,1.3f)*4.2f+noise(t,4.3f,.7f)*1.3f)*wander;
 float roll=p[state][2]+noise(t,13.7f,3.2f)*2.2f*wander;
 float f[3]={0,0,1},right[3]={1,0,0},down[3]={0,1,0};spin(f,right,yaw);spin(down,f,pitch);spin(right,down,roll);
 float k=.06f+.94f*(state==6?1:blink(fmodf(t,905.f)));
 for(int i=0;i<2;i++){float ef[3],er[3];for(int j=0;j<3;j++){ef[j]=f[j];er[j]=right[j];}spin(ef,er,i?15.46f:-15.46f);out[i]=(mori_eye_t){ef[0],ef[1],er[0],er[1]*k,down[0],down[1]*k,.186f*p[state][3],.412f*p[state][4]*(state==3?1+limit(rms,0,1)*.15f:1)};}
}
bool mori_eyes_sample(const mori_eyes_t *e,float t,float rms,mori_eye_t out[2]){
 if(e->state<0||e->state>7||!isfinite(t)||t<0||!isfinite(rms))return false;
 target(e->state,t,rms,out);float x=limit((t-e->start)/.35f,0,1),k=1-(1-x)*(1-x)*(1-x);
 if(e->transition&&k<1)for(int i=0;i<2;i++){float *a=(float*)&out[i];const float *b=(const float*)&e->from[i];for(int j=0;j<8;j++)a[j]=b[j]+(a[j]-b[j])*k;}
 return true;
}
bool mori_eyes_state(mori_eyes_t *e,int state,float t,float rms){if(state<0||state>7||!isfinite(t)||t<0)return false;if(e->state==state)return true;mori_eye_t current[2];if(!mori_eyes_sample(e,t,rms,current))return false;e->from[0]=current[0];e->from[1]=current[1];e->state=state;e->start=t;e->transition=true;return true;}
void mori_eyes_render(const mori_eye_t e[2],uint16_t *buf,int w,int h){
 if(w<=0||h<=0||w>1024||h>1024||!buf)return;
 float r=fminf(w,h)*.46f;
 for(int y=0;y<h;y++)for(int x=0;x<w;x++){
  float px=(x+.5f-w*.5f)/r,py=(y+.5f-h*.5f)/r;uint16_t color=0;
  if(px*px+py*py<1)for(int i=0;i<2;i++){
   float det=e[i].a*e[i].d-e[i].b*e[i].c;if(fabsf(det)<1e-6f)continue;
   float dx=px-e[i].x,dy=py-e[i].y;
   float u=(e[i].d*dx-e[i].c*dy)/det,v=(-e[i].b*dx+e[i].a*dy)/det;
   float rr=fminf(e[i].w,e[i].h)*.5f,ax=fmaxf(0,fabsf(u)-(e[i].w*.5f-rr)),ay=fmaxf(0,fabsf(v)-(e[i].h*.5f-rr));
   if(ax*ax+ay*ay<=rr*rr)color=0xf7be;
  }
  buf[y*w+x]=color;
 }
}

const mori_eye_skin_t mori_reference_skin={"bloub-reference-mori-mapping",mori_eyes_sample,mori_eyes_render};
