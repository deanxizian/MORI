#include "mori_ui.h"
#include <math.h>
static float clamp(float v,float a,float b){return fminf(b,fmaxf(a,v));}
void mori_head_step(mori_head_trajectory_t *h,float target,float dt){
 if(!isfinite(target)||!isfinite(dt)||dt<=0||dt>.1f)return;
 target=clamp(target,-50,50);
 float error=target-h->position;
 /* Smooth target tracking; acceleration belongs to this trajectory only. */
 float desired=clamp(2*error,-30,30);
 h->velocity+=clamp(desired-h->velocity,-60*dt,60*dt);
 float next=h->position+h->velocity*dt;
 h->position=clamp(next,-50,50);
}
float mori_head_pulse_us(float deg){return isfinite(deg)&&fabsf(deg)<=50?1500-deg*(14.0f/8)*(2000.0f/270):NAN;}
uint16_t mori_face_pixel(unsigned w,unsigned h,unsigned x,unsigned y,bool fault,bool blink){
 if(w<2||h<2||x>=w||y>=h)return 0;
 float size=(float)(w<h?w:h),nx=(2*(x+.5f)-w)/size,ny=(2*(y+.5f)-h)/size;
 if(nx*nx+ny*ny>1)return 0;
 float eye_x=fabsf(nx)-.31f,eye_y=ny+.13f;
 bool eye=fabsf(eye_x)<.10f&&fabsf(eye_y)<(blink?.015f:.15f);
 bool mouth=fabsf(nx)<.20f&&fabsf(ny-.30f)<.02f;
 return (eye||mouth)?(fault?0xf800:0x07ff):0;
}

bool mori_head_guard(mori_head_guard_t *g,uint32_t revision,bool enabled,bool fresh,float dt){
 if(!enabled||!fresh||!isfinite(dt)||dt<=0||dt>.1f){g->blocked=true;g->blocked_revision=revision;return false;}
 if(g->blocked&&g->blocked_revision==revision)return false;
 g->blocked=false;return true;
}
