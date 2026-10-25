#include "mori_runtime.h"
#include <math.h>
#include <string.h>
void mori_runtime_init(mori_runtime_t *r,mori_config_t config,bool head,bool axes){
 memset(r,0,sizeof(*r));mori_init(&r->core,config);
 atomic_init(&r->write_index,0);atomic_init(&r->read_index,0);
 atomic_init(&r->reply_write,0);atomic_init(&r->reply_read,0);
 atomic_init(&r->queue_fault,false);atomic_init(&r->queue_overflows,0);atomic_init(&r->reply_drops,0);
 r->head_verified=head;r->axes_verified=axes;
}
bool mori_runtime_enqueue(mori_runtime_t *r,mori_request_t req){
 unsigned w=atomic_load_explicit(&r->write_index,memory_order_relaxed),rd=atomic_load_explicit(&r->read_index,memory_order_acquire);
 if(w-rd>=MORI_QUEUE_CAPACITY){atomic_fetch_add(&r->queue_overflows,1);atomic_store(&r->queue_fault,true);return false;}
 r->requests[w%MORI_QUEUE_CAPACITY]=req;atomic_store_explicit(&r->write_index,w+1,memory_order_release);return true;
}
static bool take(mori_runtime_t *r,mori_request_t *req){
 unsigned rd=atomic_load_explicit(&r->read_index,memory_order_relaxed),w=atomic_load_explicit(&r->write_index,memory_order_acquire);
 if(rd==w)return false;
 *req=r->requests[rd%MORI_QUEUE_CAPACITY];atomic_store_explicit(&r->read_index,rd+1,memory_order_release);return true;
}
static void reply(mori_runtime_t *r,mori_request_t req,mori_reason_t why){
 unsigned w=atomic_load_explicit(&r->reply_write,memory_order_relaxed),rd=atomic_load_explicit(&r->reply_read,memory_order_acquire);
 if(w-rd>=MORI_REPLY_CAPACITY){atomic_fetch_add(&r->reply_drops,1);atomic_store(&r->queue_fault,true);mori_trip(&r->core,MF_QUEUE);return;}
 r->replies[w%MORI_REPLY_CAPACITY]=(mori_reply_t){req.id,req.kind,why,r->core.state,r->core.fault};
 atomic_store_explicit(&r->reply_write,w+1,memory_order_release);
}
bool mori_runtime_reply(mori_runtime_t *r,mori_reply_t *out){
 unsigned rd=atomic_load_explicit(&r->reply_read,memory_order_relaxed),w=atomic_load_explicit(&r->reply_write,memory_order_acquire);
 if(rd==w)return false;
 *out=r->replies[rd%MORI_REPLY_CAPACITY];atomic_store_explicit(&r->reply_read,rd+1,memory_order_release);return true;
}
static mori_reason_t dispatch(mori_runtime_t *r,mori_request_t req){
 mori_t *m=&r->core;
 if(req.kind==MP_INFO||req.kind==MP_STATUS)return MR_OK;
 if(req.kind==MP_HEAD){
  if(!r->head_verified)return MR_GATE;
  if(m->state==MORI_FAULT)return MR_FAULT;
  if(!isfinite(req.angle)||fabsf(req.angle)>50)return MR_RANGE;
  if(m->state==MORI_CALIBRATING||mori_health(&m->latest)!=MF_NONE)return MR_STATE;
  r->head_target=req.angle;r->head_revision++;r->head_active=true;return MR_OK;
 }
 if(req.kind!=MP_CORE)return MR_SYNTAX;
 if(req.command.type==MC_CONFIRM_SIGNS&&!r->axes_verified)return MR_GATE;
 if(req.command.type==MC_ARM_BALANCE&&(!m->cfg.balance_enabled||!m->cfg.power_verified||!r->axes_verified))return MR_GATE;
 if(req.command.type==MC_ARM_BENCH&&!m->cfg.power_verified)return MR_GATE;
 if(mori_command(m,req.command)){
  if(req.command.type==MC_DISARM||req.command.type==MC_ACK)r->head_active=false;
  return MR_OK;
 }
 return m->state==MORI_FAULT?MR_FAULT:MR_STATE;
}
static void histogram(uint32_t *h,uint32_t v){unsigned i=v?((v-1)/100):0;if(i>32)i=32;h[i]++;}
uint32_t mori_hist_quantile_upper(const uint32_t h[33],unsigned p){
 uint64_t count=0;for(unsigned i=0;i<33;i++)count+=h[i];if(!count||!p||p>100)return 0;
 uint64_t rank=(count*p+99)/100,sum=0;
 for(unsigned i=0;i<33;i++){sum+=h[i];if(sum>=rank)return i==32?UINT32_MAX:(i+1)*100;}
 return UINT32_MAX;
}
void mori_runtime_frame(mori_runtime_t *r,const mori_hal_t *h){
 uint64_t begin=h->now_us(h->context);mori_sample_t s={0};mori_timing_t t={0};
 /* Aggregate the preceding completed frame before publishing it. No sampled
  * frame bias, and histogram work belongs to the current execution budget. */
 if(r->frames){histogram(r->total_hist,r->timing.total_us);histogram(r->wake_hist,r->timing.wake_us);histogram(r->jitter_hist,r->timing.jitter_us);}
 h->sample(h->context,&s,&t);s.now_us=h->now_us(h->context);
 r->core.clock_us=h->now_us;r->core.clock_context=h->context;
 uint64_t core_begin=h->now_us(h->context);mori_step(&r->core,&s);
 t.fusion_us=r->core.fusion_us;
 mori_request_t req;
 if(atomic_exchange(&r->queue_fault,false)){
  mori_trip(&r->core,MF_QUEUE);
  /* Bounded draining: queued recovery/arm commands never recover this overflow. */
  for(unsigned i=0;i<MORI_QUEUE_CAPACITY&&take(r,&req);i++)reply(r,req,MR_QUEUE);
 }else{
  for(int k=0;k<2&&take(r,&req);k++)reply(r,req,dispatch(r,req));
 }
 t.core_us=(uint32_t)(h->now_us(h->context)-core_begin);
 t.feedback_us=t.core_us>=t.fusion_us?t.core_us-t.fusion_us:0;
 uint64_t before_pwm=h->now_us(h->context);
 if(before_pwm-begin>MORI_COMPUTE_BUDGET_US)mori_trip(&r->core,MF_TIMING);
 if(r->core.state==MORI_BENCH&&before_pwm+MORI_BENCH_CUTOFF_MARGIN_US>=r->core.bench_deadline_us){
  r->core.state=MORI_READY;r->core.bench_left=r->core.bench_right=0;r->core.out.enable=false;
 }
 h->apply(h->context,r->core.out);
 uint64_t end=h->now_us(h->context);t.pwm_submit_us=(uint32_t)(end-before_pwm);
 if(end-begin>MORI_COMPUTE_BUDGET_US){mori_trip(&r->core,MF_TIMING);h->apply(h->context,r->core.out);end=h->now_us(h->context);}
 if(r->core.state==MORI_FAULT||mori_health(&r->core.latest)!=MF_NONE)r->head_active=false;
 if(h->after_apply)h->after_apply(h->context);
 if(r->previous_begin){uint64_t d=begin-r->previous_begin;t.jitter_us=(uint32_t)(d>MORI_NOMINAL_PERIOD_US?d-MORI_NOMINAL_PERIOD_US:MORI_NOMINAL_PERIOD_US-d);}
 r->previous_begin=begin;r->frames++;
 #define MAX_FIELD(f) if(t.f>r->maxima.f)r->maxima.f=t.f
 MAX_FIELD(imu_io_us);MAX_FIELD(monitor_io_us);MAX_FIELD(encoder_us);MAX_FIELD(wake_us);MAX_FIELD(core_us);MAX_FIELD(fusion_us);MAX_FIELD(feedback_us);MAX_FIELD(pwm_submit_us);MAX_FIELD(jitter_us);
 #undef MAX_FIELD
 end=h->now_us(h->context);t.total_us=(uint32_t)(end-begin);
 if(t.total_us>MORI_COMPUTE_BUDGET_US){mori_trip(&r->core,MF_TIMING);r->head_active=false;h->apply(h->context,r->core.out);t.total_us=(uint32_t)(h->now_us(h->context)-begin);}
 r->timing=t;if(t.total_us>r->maxima.total_us)r->maxima.total_us=t.total_us;
 bool healthy=r->core.state!=MORI_FAULT&&mori_health(&r->core.latest)==MF_NONE&&t.total_us<=MORI_COMPUTE_BUDGET_US;
 if(healthy){r->heartbeat_level=!r->heartbeat_level;h->heartbeat(h->context,r->heartbeat_level);}
}
