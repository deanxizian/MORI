#include "mori_v1.h"
#include <string.h>
#include <math.h>
static float clamp(float x,float lo,float hi){return fminf(hi,fmaxf(lo,x));}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void freeze_head(mori_v1_t *v){for(unsigned i=0;i<2;i++){v->head[i].target=v->head[i].position;v->head[i].velocity=0;}}
static uint64_t u64(const uint8_t *p){return (uint64_t)u32(p)|(uint64_t)u32(p+4)<<32;}
void mori_v1_init(mori_v1_t *v,uint64_t session){
 memset(v,0,sizeof(*v));v->session=session;v->last_result=V1_REJECTED;mori_init(&v->core,(mori_config_t){0});
 v->head[0]=(mori_axis_t){.minimum=-1.0471975512f,.maximum=1.0471975512f,.sign=1,.max_velocity=.52f,.max_acceleration=1.05f};
 v->head[1]=(mori_axis_t){.minimum=-.3490658504f,.maximum=.436332313f,.sign=1,.max_velocity=.52f,.max_acceleration=1.05f};
}
bool mori_axis_target(mori_axis_t *a,float rad){if(!isfinite(rad)||rad<a->minimum||rad>a->maximum)return false;a->target=rad;return true;}
void mori_axis_step(mori_axis_t *a,float dt,bool inhibit){
 if(inhibit||!isfinite(dt)||dt<=0||dt>.05f){a->target=a->position;a->velocity=0;return;}
 float error=a->target-a->position,desired=copysignf(fminf(a->max_velocity,sqrtf(2*a->max_acceleration*fabsf(error))),error);
 a->velocity+=clamp(desired-a->velocity,-a->max_acceleration*dt,a->max_acceleration*dt);
 float step=a->velocity*dt;
 if(step*error>=0&&fabsf(step)>=fabsf(error)){a->position=a->target;a->velocity=0;}else a->position=clamp(a->position+step,a->minimum,a->maximum);
 /* Hold command at rest. Never automatically release pitch holding torque. */
}
static mori_v1_result_t dispatch(mori_v1_t *v,unsigned kind,const uint8_t *p,unsigned n,uint64_t now){
 if(n<10)return V1_REJECTED;
 uint64_t basis=u64(p);unsigned ttl=p[8]|p[9]<<8;p+=10;n-=10;
 if(ttl==0||ttl>300||basis>now||now-basis>=ttl)return V1_EXPIRED;
 float args[2]={0};if(n>sizeof(args))return V1_REJECTED;memcpy(args,p,n);
 if(kind==MORI_READ_STATUS&&n==0)return V1_COMPLETED;
 if(kind==MORI_FAULT_STOP&&n==0){mori_trip(&v->core,MF_CONFIG);v->claimed=false;freeze_head(v);return V1_FAULT;}
 if(kind==MORI_STOP_MOTION&&n==0){v->yaw_rate_target=0;mori_command(&v->core,(mori_command_t){.type=MC_STOP});return V1_COMPLETED;}
 if(kind==MORI_CLAIM_CONTROL&&n==1&&p[0]==1){v->claimed=true;v->lease_end_ms=basis+ttl;return V1_COMPLETED;}
 if(!v->claimed||now>=v->lease_end_ms)return V1_REJECTED;
 if(kind==MORI_HEARTBEAT&&n==0){v->lease_end_ms=basis+ttl;return V1_COMPLETED;}
 if(kind==MORI_RELEASE_CONTROL&&n==0){v->claimed=false;mori_command(&v->core,(mori_command_t){.type=MC_STOP});v->yaw_rate_target=0;freeze_head(v);return V1_COMPLETED;}
 if(kind==MORI_DISARM&&n==1&&p[0]==1){if(!mori_command(&v->core,(mori_command_t){.type=MC_DISARM}))return V1_REJECTED;freeze_head(v);return V1_COMPLETED;}
 if(kind==MORI_ACK_FAULT&&n==1&&p[0]==1)return mori_command(&v->core,(mori_command_t){.type=MC_ACK})?V1_COMPLETED:V1_REJECTED;
 if(kind==MORI_ENTER_MAINTENANCE&&n==1&&p[0]==1&&v->core.state==MORI_DISARMED){v->maintenance=true;return V1_COMPLETED;}
 if(kind==MORI_ARM&&n==1&&p[0]==1&&v->physical_contract_verified&&!v->maintenance)return mori_command(&v->core,(mori_command_t){.type=MC_ARM_BALANCE})?V1_COMPLETED:V1_REJECTED;
 if(kind==MORI_HEAD_TARGET&&v->core.state==MORI_BALANCE&&!v->maintenance&&n==8&&mori_v1_numeric_valid(kind,args,2)&&v->physical_contract_verified&&v->head[0].verified&&v->head[1].verified){mori_axis_target(&v->head[0],args[0]);mori_axis_target(&v->head[1],args[1]);return V1_RUNNING;}
 /* Old MC_MOVE.b is differential PWM, not rad/s. No unmeasured conversion is supplied. */
 if(kind==MORI_SET_VELOCITY&&n==8&&mori_v1_numeric_valid(kind,args,2)&&v->physical_contract_verified&&args[1]==0&&!v->maintenance)return mori_command(&v->core,(mori_command_t){.type=MC_MOVE,.a=args[0],.b=0})?V1_RUNNING:V1_REJECTED;
 return V1_REJECTED; /* Autonomous target executor exists in simulation; physical gate stays closed. */
}
mori_v1_result_t mori_v1_feed(mori_v1_t *v,uint8_t b,uint64_t now,bool *complete){
 *complete=mori_wire_feed(&v->wire,b,now);if(!*complete)return V1_REJECTED;
 const uint8_t *p=v->wire.bytes;uint64_t session=u64(p+10),id=u64(p+18);uint32_t sequence=u32(p+6);unsigned kind=p[3],n=p[4]|p[5]<<8;
 if(session!=v->session||!sequence||sequence>0x7fffffffu){v->rejected++;return V1_REJECTED;}
 for(unsigned i=0;i<v->result_count;i++)if(id==v->results[i].id)return v->results[i].result; /* Retained retries never renew a lease or execute twice. */
 if(sequence<=v->sequence&&kind!=MORI_STOP_MOTION&&kind!=MORI_FAULT_STOP){v->rejected++;return V1_REJECTED;}
 if(sequence>v->sequence)v->sequence=sequence;
 v->last_id=id;v->last_result=dispatch(v,kind,p+26,n,now);
 v->results[v->result_next]=(mori_v1_cached_result_t){id,v->last_result};
 v->result_next=(v->result_next+1)%MORI_V1_RESULT_CACHE;
 if(v->result_count<MORI_V1_RESULT_CACHE)v->result_count++;
 if(v->last_result==V1_REJECTED)v->rejected++;return v->last_result;
}
void mori_v1_tick(mori_v1_t *v,uint64_t now,const mori_sample_t *sample){
 if(sample)mori_step(&v->core,sample);
 if(v->claimed&&now>=v->lease_end_ms){v->claimed=false;v->yaw_rate_target=0;mori_command(&v->core,(mori_command_t){.type=MC_STOP});}
 bool inhibit=!v->claimed||v->core.state!=MORI_BALANCE||v->maintenance||!v->physical_contract_verified||v->core.out.low_battery||fabsf(v->core.theta)>.174532925f;
 float dt=v->last_ms?(now-v->last_ms)*.001f:.01f;v->last_ms=now;
 for(int i=0;i<2;i++)mori_axis_step(&v->head[i],dt,inhibit||!v->head[i].verified);
}
