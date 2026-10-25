#include "timing.h"
#include <limits.h>
static void add(uint32_t *v){if(*v<UINT32_MAX)(*v)++;}
bool mori_timing_mark(mori_timing *t,enum mori_timing_stage stage,uint64_t now){
 if(!t||(unsigned)stage>=T_STAGES)return false;
 if(stage==T_DRDY){
  if(t->next&&t->next!=T_STAGES)add(&t->invalid_frames);
  if(t->have_previous){if(now<=t->previous_drdy||now-t->previous_drdy>UINT32_MAX){add(&t->invalid_frames);t->valid=false;t->next=0;return false;}uint32_t dt=(uint32_t)(now-t->previous_drdy);if(dt>t->period_max_us)t->period_max_us=dt;}
  t->have_previous=true;t->previous_drdy=now;t->valid=true;t->next=0;
 }
 if(!t->valid||(unsigned)stage!=t->next||(stage&&now<t->stamp[stage-1])){t->valid=false;add(&t->invalid_frames);return false;}
 t->stamp[stage]=now;t->next++;
 if(stage==T_WHEEL_TC){
  if(now-t->stamp[T_WAKE]>UINT32_MAX){t->valid=false;add(&t->invalid_frames);return false;}
  for(unsigned i=0;i<T_STAGES-1;i++){
   uint64_t delta=t->stamp[i+1]-t->stamp[i];if(delta>UINT32_MAX){t->valid=false;add(&t->invalid_frames);return false;}
   t->last_us[i]=(uint32_t)delta;if(delta>t->max_us[i])t->max_us[i]=(uint32_t)delta;
   unsigned bucket=delta/100<31?(unsigned)(delta/100):31;add(&t->histogram[i][bucket]);
  }
  uint32_t execution=(uint32_t)(now-t->stamp[T_WAKE]);if(execution>t->execution_max_us)t->execution_max_us=execution;add(&t->frames);
 }
 return true;
}
