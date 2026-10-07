#include "mori_core.h"
#include <math.h>
#include <string.h>
static float clampf(float x,float a,float b){return fminf(b,fmaxf(a,x));}
static bool armed(const mori_t*m){return m->state==MORI_BENCH||m->state==MORI_BALANCE;}
static bool fresh(uint64_t n,uint64_t t,uint64_t age){return t<=n&&n-t<=age;}
static bool finite_sample(const mori_sample_t*s){return isfinite(s->ax)&&isfinite(s->ay)&&isfinite(s->az)&&isfinite(s->gy)&&isfinite(s->v_left)&&isfinite(s->v_right)&&isfinite(s->battery_v)&&isfinite(s->bus_a)&&isfinite(s->temp_left_c)&&isfinite(s->temp_right_c);}
mori_fault_t mori_health(const mori_sample_t*s){
    if(!s->estop_ok)return MF_ESTOP;
    if(!s->driver_ok)return MF_DRIVER;
    if(!finite_sample(s)||!s->imu_ok||!s->monitor_ok||!fresh(s->now_us,s->imu_us,8000)||!fresh(s->now_us,s->monitor_us,50000))return MF_SENSOR;
    if(!s->encoders_ok)return MF_ENCODER;
    if(s->battery_v<6.0f)return MF_LOW_VOLTAGE;
    if(s->battery_v>8.65f)return MF_OVERVOLTAGE;
    if(fabsf(s->bus_a)>1.30f)return MF_CURRENT; /* bus current, not individual phase current */
    if(s->temp_left_c>65||s->temp_right_c>65||s->temp_left_c<0||s->temp_right_c<0)return MF_TEMPERATURE;
    return MF_NONE;
}
void mori_init(mori_t*m,mori_config_t cfg){memset(m,0,sizeof(*m));m->cfg=cfg;m->state=MORI_DISARMED;}
void mori_trip(mori_t*m,mori_fault_t f){if(m->state!=MORI_FAULT)m->fault=f;m->state=MORI_FAULT;m->out=(mori_output_t){0};m->v_target=m->v_ref=m->yaw_target=m->yaw_ref=m->velocity_i=0;m->bench_left=m->bench_right=0;}
static bool ready(mori_t*m){return m->have_sample&&m->calibrated&&mori_health(&m->latest)==MF_NONE&&m->latest.battery_v>=6.8f&&fabsf(m->theta)<0.05236f&&fabsf(m->latest.gy-m->bias)<.15f;}
bool mori_command(mori_t*m,mori_command_t c){
    if(!isfinite(c.a)||!isfinite(c.b)||!isfinite(c.c)||!isfinite(c.d))return false;
    uint64_t now=m->latest.now_us;
    switch(c.type){
    case MC_DISARM:
        if(m->state==MORI_FAULT)return false; /* only ACK can leave a latched fault */
        m->state=MORI_DISARMED;m->out=(mori_output_t){0};m->bench_left=m->bench_right=0;m->v_target=m->v_ref=m->yaw_target=m->yaw_ref=m->velocity_i=0;return true;
    case MC_ACK:
        if(m->state!=MORI_FAULT||!m->have_sample||mori_health(&m->latest)!=MF_NONE||fabsf(m->theta)>.0873f)return false;
        m->state=MORI_DISARMED;m->fault=MF_NONE;m->calibrated=false;m->signs_confirmed=false;return true;
    case MC_CALIBRATE:
        if(armed(m)||m->state==MORI_FAULT||!m->have_sample||mori_health(&m->latest)!=MF_NONE)return false;
        m->state=MORI_CALIBRATING;m->calibrated=false;m->calibration_count=0;m->gyro_sum=m->gyro_sum2=0;return true;
    case MC_CONFIRM_SIGNS:
        if(armed(m)||m->state==MORI_FAULT)return false;
        m->signs_confirmed=true;return true;
    case MC_GAINS:
        if(armed(m)||m->state==MORI_FAULT||c.a<=0||c.a>10||c.b<=0||c.b>2||c.c<0||c.c>1||c.d<0||c.d>.2)return false;
        m->cfg.kp=c.a;m->cfg.kd=c.b;m->cfg.kv=c.c;m->cfg.ki=c.d;return true;
    case MC_ARM_BENCH:
        if(m->state!=MORI_READY||!m->cfg.power_verified||!ready(m))return false;
        m->state=MORI_BENCH;m->bench_deadline_us=now+200000;m->last_command_us=now;return true;
    case MC_BENCH_DUTY:
        if(m->state!=MORI_BENCH||now>=m->bench_deadline_us||fabsf(c.a)>.12f||fabsf(c.b)>.12f)return false;
        m->bench_left=c.a;m->bench_right=c.b;return true; /* NEVER extends the bench deadline */
    case MC_ARM_BALANCE:
        if(m->state!=MORI_READY||!m->cfg.power_verified||!m->cfg.balance_enabled||!m->signs_confirmed||!isfinite(m->cfg.kp)||!isfinite(m->cfg.kd)||!isfinite(m->cfg.kv)||!isfinite(m->cfg.ki)||m->cfg.kp<=0||m->cfg.kp>10||m->cfg.kd<=0||m->cfg.kd>2||m->cfg.kv<0||m->cfg.kv>1||m->cfg.ki<0||m->cfg.ki>.2f||!ready(m))return false;
        m->state=MORI_BALANCE;m->v_ref=m->v_target=m->yaw_target=m->yaw_ref=m->velocity_i=0;
        m->saturation_us=m->stall_left_us=m->stall_right_us=0;m->last_command_us=now;return true;
    case MC_MOVE:
        if(m->state!=MORI_BALANCE||fabsf(c.a)>.3f||fabsf(c.b)>.10f)return false;
        if(m->latest.battery_v<6.8f&&(c.a!=0||c.b!=0))return false;
        m->v_target=c.a;m->yaw_target=c.b;m->last_command_us=now;return true;
    case MC_STOP:
        m->v_target=0;m->yaw_target=0;m->last_command_us=now;
        if(m->state==MORI_BENCH){m->state=MORI_READY;m->bench_left=m->bench_right=0;m->out=(mori_output_t){0};}
        return true;
    }
    return false;
}
mori_output_t mori_step(mori_t*m,const mori_sample_t*s){
    uint64_t fusion_start=m->clock_us?m->clock_us(m->clock_context):0;
    bool repeated=m->have_sample && s->imu_us<=m->previous_imu_us;
    m->previous_imu_us=s->imu_us;
    m->latest=*s;m->have_sample=true;
    if(repeated)m->latest.imu_ok=false;
    float dt=m->previous_us?(float)(s->now_us-m->previous_us)*1e-6f:1.0f/416.0f;
    if(m->previous_us&&s->now_us<=m->previous_us){if(armed(m))mori_trip(m,MF_TIMING);dt=1.0f/416;}
    m->previous_us=s->now_us;
    mori_fault_t f=mori_health(&m->latest);
    if((f==MF_ESTOP||f==MF_DRIVER)&&m->state!=MORI_FAULT)mori_trip(m,f);
    if(m->state!=MORI_DISARMED && m->state!=MORI_FAULT && f!=MF_NONE)mori_trip(m,f);
    if(armed(m)&&(f!=MF_NONE||dt>.006f||dt<.001f))mori_trip(m,f!=MF_NONE?f:MF_TIMING);
    if(f==MF_NONE){
        float an=sqrtf(s->ax*s->ax+s->ay*s->ay+s->az*s->az),acc=atan2f(-s->ax,s->az);
        if(!m->calibrated)m->theta=acc;
        else{
            float predicted=m->theta+(s->gy-m->bias)*clampf(dt,.001f,.006f);
            float alpha=.5f/(.5f+dt);
            m->theta=(an>8.8f&&an<10.8f)?alpha*predicted+(1-alpha)*acc:predicted;
        }
        if(m->state==MORI_CALIBRATING){
            bool still=fabsf(s->gy)<.08f&&fabsf(an-9.80665f)<.35f&&fabsf(acc)<.05236f&&fabsf(s->v_left)<.01f&&fabsf(s->v_right)<.01f;
            if(!still){m->calibration_count=0;m->gyro_sum=m->gyro_sum2=0;}
            else{m->gyro_sum+=s->gy;m->gyro_sum2+=(double)s->gy*s->gy;m->calibration_count++;}
            if(m->calibration_count==1024){
                double mean=m->gyro_sum/1024,variance=m->gyro_sum2/1024-mean*mean;
                if(variance>.0001){m->calibration_count=0;m->gyro_sum=m->gyro_sum2=0;}
                else{m->bias=(float)mean;m->calibrated=true;m->state=MORI_READY;}
            }
        }
    }else if(m->state==MORI_CALIBRATING){m->state=MORI_DISARMED;m->calibration_count=0;}
    m->fusion_us=m->clock_us?(uint32_t)(m->clock_us(m->clock_context)-fusion_start):0;
    m->out=(mori_output_t){.low_battery=s->battery_v<6.8f,.request_support=s->battery_v<6.6f};
    if(!armed(m))return m->out;
    if(fabsf(m->theta)>.349066f){mori_trip(m,MF_TILT);return m->out;}
    if(m->state==MORI_BENCH){
        if(s->now_us+MORI_BENCH_CUTOFF_MARGIN_US>=m->bench_deadline_us){m->state=MORI_READY;m->bench_left=m->bench_right=0;return m->out;}
        m->out.left=m->bench_left;m->out.right=m->bench_right;m->out.enable=true;return m->out;
    }
    if(s->now_us-m->last_command_us>500000||s->battery_v<6.8f){m->v_target=m->yaw_target=0;}
    m->v_ref+=clampf(m->v_target-m->v_ref,-.2f*dt,.2f*dt); /* motion ramp only */
    float ve=m->v_ref-.5f*(s->v_left+s->v_right);
    float theta_ref=clampf(m->cfg.kv*ve+m->velocity_i,-.087266f,.087266f);
    float raw=m->cfg.kp*(m->theta-theta_ref)+m->cfg.kd*(s->gy-m->bias);
    m->yaw_ref+=clampf(m->yaw_target-m->yaw_ref,-.4f*dt,.4f*dt);
    float u=clampf(raw,-.65f,.65f),yaw=clampf(m->yaw_ref,-(.65f-fabsf(u)),.65f-fabsf(u));
    /* Positive velocity error requests forward lean. At zero lean this initially
       commands a small backward wheel torque to initiate that lean (nonminimum
       phase body/wheel response); there is no competing wheel-speed PID. */
    bool saturated=fabsf(raw)>.65f;
    if(!saturated&&fabsf(theta_ref)<.08726f)m->velocity_i=clampf(m->velocity_i+m->cfg.ki*ve*dt,-.04f,.04f);
    if(saturated){if(!m->saturation_us)m->saturation_us=s->now_us;if(s->now_us-m->saturation_us>200000)mori_trip(m,MF_SATURATION);}else m->saturation_us=0;
    float outs[2]={u-yaw,u+yaw},vs[2]={s->v_left,s->v_right};uint64_t*stall[2]={&m->stall_left_us,&m->stall_right_us};
    for(int k=0;k<2;k++){
        if(fabsf(outs[k])>.20f&&fabsf(vs[k])<.004f){if(!*stall[k])*stall[k]=s->now_us;if(s->now_us-*stall[k]>200000)mori_trip(m,MF_ENCODER);}else *stall[k]=0;
    }
    if(m->state==MORI_BALANCE){m->out.left=outs[0];m->out.right=outs[1];m->out.enable=true;}
    return m->out;
}
const char*mori_state_name(mori_state_t s){static const char*n[]={"DISARMED","CALIBRATING","READY","BENCH","BALANCE","FAULT"};return s>=MORI_DISARMED&&s<=MORI_FAULT?n[s]:"INVALID";}

const char*mori_fault_name(mori_fault_t f){static const char*n[]={"NONE","SENSOR","ESTOP","DRIVER","LOW_VOLTAGE","OVERVOLTAGE","CURRENT","TEMPERATURE","TILT","ENCODER","SATURATION","TIMING","QUEUE","CONFIG"};return f>=MF_NONE&&f<=MF_CONFIG?n[f]:"INVALID";}
