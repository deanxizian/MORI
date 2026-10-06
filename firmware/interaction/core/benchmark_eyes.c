#define _POSIX_C_SOURCE 200809L
#include "eyes.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static uint16_t pixels[360*360];
static double time_us(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e6+t.tv_nsec/1e3;}
static int compare(const void *a,const void *b){double x=*(const double *)a,y=*(const double *)b;return (x>y)-(x<y);}
int main(void){
 mori_eyes_t e={0};double elapsed[240];
 for(unsigned i=0;i<240;i++){
  float t=i/25.f;mori_eye_t eyes[2];
  if(i%13==0)assert(mori_eyes_state(&e,(i/13)%8,t,0));
  double start=time_us();assert(mori_eyes_sample(&e,t,.2f,eyes));mori_eyes_render(eyes,pixels,360,360);elapsed[i]=time_us()-start;
  for(int y=0;y<360;y++)for(int x=0;x<360;x++)if(hypot(x-180.,y-180.)>180)assert(pixels[y*360+x]==0);
 }
 qsort(elapsed,240,sizeof(double),compare);
 printf("{\"source\":\"HOST_TEST\",\"hardware\":\"NOT_TESTED\",\"resolution\":[360,360],\"frames\":240,\"framebuffer_bytes\":%zu,\"p50_us\":%.3f,\"p95_us\":%.3f,\"p99_us\":%.3f,\"max_us\":%.3f}\n",sizeof(pixels),elapsed[119],elapsed[227],elapsed[236],elapsed[239]);
 return 0;
}
