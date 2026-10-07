#include "mori12.h"
#include <math.h>
#include <string.h>
static double clamp(double x,double l,double h){return fmax(l,fmin(x,h));}
void mori_motion_init(mori_motion *m){if(m){memset(m,0,sizeof(*m));m->state=M_BOOT;m->external_inhibit_requested=true;m->head_inhibited=true;m->state=M_SELF_TEST;m->state=M_DISARMED;}}
bool mori_parameters_valid(const mori_parameters *p){
 if(!p||!p->physical_verified||!p->axes_verified||!p->parameters_verified||!p->version)return false;
 const double values[]={p->wheel_radius_m,p->torque_limit_nm,p->kp_pitch,p->kd_pitch,p->kp_speed,p->ki_speed,p->max_pitch_ref_rad,p->severe_tilt_rad};
 for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);i++)if(!isfinite(values[i])||values[i]<0)return false;
 return p->wheel_radius_m>0&&p->torque_limit_nm>0&&p->kp_pitch>0&&p->kd_pitch>0&&p->severe_tilt_rad>p->max_pitch_ref_rad&&p->severe_tilt_rad<1&&p->max_pitch_ref_rad>0&&p->imu_age_us&&p->wheel_age_us&&p->skew_us&&p->max_control_gap_us&&p->saturation_us;
}
bool mori_motion_configure(mori_motion *m,const mori_parameters *p,bool supported){
 if(!m||!supported||m->state!=M_DISARMED||!mori_parameters_valid(p))return false;
 m->parameters=*p;return true;
}
static mori_fault health(const mori_motion *m,const mori_sample *s,uint64_t now){
 const mori_parameters *p=&m->parameters;
 if(!s||!isfinite(s->pitch_rad)||!isfinite(s->pitch_rate_rad_s)||!isfinite(s->velocity_m_s))return F_INPUT;
 if(!s->estop_ok)return F_ESTOP;
 if(!s->power_ok)return F_POWER;
 if(!s->imu_valid||s->imu_us>now||now-s->imu_us>p->imu_age_us)return F_IMU;
 for(unsigned i=0;i<2;i++)if(!s->wheel_valid[i]||s->wheel_us[i]>now||now-s->wheel_us[i]>p->wheel_age_us)return F_WHEEL;
 uint64_t a=s->wheel_us[0],b=s->wheel_us[1];if((a>b?a-b:b-a)>p->skew_us)return F_WHEEL;
 if(fabs(s->pitch_rad)>=p->severe_tilt_rad)return F_TILT;
 return F_NONE;
}
bool mori_motion_arm(mori_motion *m,const mori_sample *s,uint64_t now,bool confirm){
 if(!m||!confirm||m->state!=M_DISARMED||m->fault||!mori_parameters_valid(&m->parameters)||health(m,s,now)||s->low_battery)return false;
 m->state=M_ARMED_IDLE;m->drive_requested=true;m->external_inhibit_requested=false;m->have_frame=false;m->integral=0;m->saturating=false;m->saturated_since_us=0;m->last_frame_us=now;return true;
}
bool mori_motion_target(mori_motion *m,double v,double turn,uint64_t now,uint32_t lease){
 if(!m||!m->drive_requested||m->fault||!isfinite(v)||!isfinite(turn)||fabs(v)>.10||fabs(turn)>m->parameters.torque_limit_nm||!lease||lease>300000||UINT64_MAX-now<lease)return false;
 m->target_v=v;m->target_turn_nm=turn;m->lease_end_us=now+lease;m->state=M_MOVING;return true;
}
void mori_motion_stop(mori_motion *m){if(m){m->target_v=m->target_turn_nm=0;m->lease_end_us=0;if(m->drive_requested)m->state=M_ARMED_IDLE;}}
void mori_motion_fault(mori_motion *m,mori_fault f){if(!m)return;if(!m->fault)m->fault=f?f:F_INPUT;m->drive_requested=false;m->external_inhibit_requested=true;m->head_inhibited=true;m->left_nm=m->right_nm=m->limited_v=m->integral=0;mori_motion_stop(m);m->state=M_FAULT;}
bool mori_motion_disarm(mori_motion *m,bool support){if(!m||!support)return false;if(m->state==M_FAULT)return false;mori_motion_stop(m);m->drive_requested=false;m->external_inhibit_requested=true;m->left_nm=m->right_nm=m->integral=m->limited_v=0;m->head_inhibited=true;m->state=M_DISARMED;return true;}
bool mori_motion_ack(mori_motion *m,bool support,bool confirm){if(!m||m->state!=M_FAULT||!support||!confirm)return false;m->fault=F_NONE;m->state=M_DISARMED;m->have_frame=false;return true;}
void mori_motion_step(mori_motion *m,const mori_sample *s,uint64_t now){
 if(!m||!m->drive_requested)return;
 mori_fault f=health(m,s,now);if(f){mori_motion_fault(m,f);return;}
 if(m->have_frame&&(now<=m->last_frame_us||now-m->last_frame_us>m->parameters.max_control_gap_us)){mori_motion_fault(m,F_CONTROL_TIMEOUT);return;}
 double dt=m->have_frame?(now-m->last_frame_us)*1e-6:0;m->last_frame_us=now;m->have_frame=true;
 if(!m->lease_end_us||now>=m->lease_end_us||s->low_battery)mori_motion_stop(m);
 m->head_inhibited=s->low_battery||!s->head_valid||fabs(s->pitch_rad)>.174532925;
 if(!s->head_valid&&m->state==M_AUTONOMY)mori_motion_stop(m);
 /* Limit navigation acceleration only. Never slew-limit balance correction. */
 m->limited_v=clamp(m->target_v,m->limited_v-.2*dt,m->limited_v+.2*dt);
 const mori_parameters *p=&m->parameters;double e=m->limited_v-s->velocity_m_s;
 double next_i=clamp(m->integral+p->ki_speed*e*dt,-p->max_pitch_ref_rad,p->max_pitch_ref_rad);
 double desired=p->kp_speed*e+next_i;
 if(fabs(desired)<=p->max_pitch_ref_rad||desired*e<0)m->integral=next_i;
 m->pitch_reference_rad=clamp(p->kp_speed*e+m->integral,-p->max_pitch_ref_rad,p->max_pitch_ref_rad);
 double raw=p->kp_pitch*(s->pitch_rad-m->pitch_reference_rad)+p->kd_pitch*s->pitch_rate_rad_s;
 if(!isfinite(raw)){mori_motion_fault(m,F_INPUT);return;}
 double common=clamp(raw,-p->torque_limit_nm,p->torque_limit_nm),margin=p->torque_limit_nm-fabs(common);
 double turn=clamp(m->target_turn_nm,-margin,margin);m->left_nm=common-turn;m->right_nm=common+turn;
 bool saturated=fabs(raw)>=p->torque_limit_nm;
 if(saturated){if(!m->saturating){m->saturating=true;m->saturated_since_us=now;}else if(now-m->saturated_since_us>=p->saturation_us){mori_motion_fault(m,F_SATURATION);return;}}
 else m->saturating=false;
 m->healthy_frames++;m->heartbeat_edge=!m->heartbeat_edge;
}
