#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Arrow-key references around the unchanged trial113 selected balance gains.

No raw wheel drive bypass. Forward/back changes the speed reference; turning
changes the existing relative encoder-heading reference. Release slews to
zero and captures the stopping reference, without resetting the pitch PID.
The3cm differential guard follows commanded turn intent. The operator has
removed demo net/path distance stops; odometry remains recorded. All other
torque/posture/timing/thermal guards and the finite run duration remain.
"""
import json,math,sys
from air_trial import main as trial_main
from attitude import Fault,clip,finite
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from remote_drive_keys import Keys,KeyWorker
from ground_trial import ground_command
from two_deck_live_causal_velocity import CausalVelocityReference
from two_deck_native_240_speed025 import PLAN as BASE,NativeDampingController
START='--run-two-deck-remote-drive'
PLAN=dict(BASE,name='two_deck_remote_drive_v184',ap_ki=.15/BASE['output_scale_nm'],
    ap_kd=.15/BASE['output_scale_nm'],speed_kp_rad_per_m_s=.35,
    net_rolling_limit_m=None,rolling_path_limit_m=None,
    control_phase='two_deck_remote_drive',
    active_message='REMOTE_DRIVE_ACTIVE: 平衡补偿已开始，红点亮、一声后手只防倒。保持P3.50/I0.15/D0.150/车速P0.35/本地阻尼0.24。方向键按住持续运动，松键减速后就地保持；返回/确认停止移动但保留平衡。转向目标4.0rad/s轮速差。前后采用平滑起停曲线，松键即消退行驶积分；停车后2厘米范围内不追回原位置，姿态和零速反馈继续。最长30分钟，不设净转量或累计转量停止；原力矩/速度/姿态/温度/通信保护保留，左右差值保护跟随转向目标；红点灭、两声后接住。')

class DriveVelocityProfile:
    """Exact two-pole reference shaping, tau0.20s; never a motor-rate limiter.

    Both stages have positive unit-gain kernels, so bounded references remain
    bounded. Retain the old0.30m/s2 cap even on full direction reversal.
    Targets remain +/-0.12m/s. No minimum hold, latch or hidden cruise;
    release/disconnect target is zero. Tiny tails are explicitly ended.
    """
    def __init__(self):self.lead=0.;self.velocity=0.
    def update(self,target,dt):
        finite(target,dt)
        if abs(target)>.12+1e-12 or not 0<dt<=.025:
            raise Fault('remote_profile_outside_plan')
        decay=math.exp(-dt/.20);old_lead=self.lead
        self.lead=target+(old_lead-target)*decay
        proposed=target+(self.velocity-target+(old_lead-target)*dt/.20)*decay
        self.velocity+=clip(proposed-self.velocity,.30*dt)
        if target==0. and max(abs(self.lead),abs(self.velocity))<.0001:
            self.lead=self.velocity=0.
        return self.velocity

class RemoteVelocityReference(CausalVelocityReference):
    """Separate driving target from the unchanged3cm/s idle position return.

    Same measured velocity, filter, P gain,3degree pitch and6degree/s slew.
    Remote-only integral removes sustained tracking bias within0.75degree.
    Initial/idle neutral frames execute the original reference path exactly.
    """
    def __init__(self):
        super().__init__();self.remote_speed_integral_rad=0.

    def __call__(self,a,speeds,plan):
        previous_reference,previous_t=self.pitch_reference_deg,self.previous_t
        result=super().__call__(a,speeds,plan)
        if 'remote_velocity_target_m_s' not in a:
            self.remote_speed_integral_rad=0.
            return result
        target=a['remote_velocity_target_m_s'];finite(target)
        if abs(target)>.12+1e-12:raise Fault('remote_velocity_target_outside_plan')
        dt=a['dt'] if previous_t is None else a['t']-previous_t
        error_v=target-self.filtered_velocity
        old_i=self.remote_speed_integral_rad
        candidate=clip(old_i+.20*error_v*dt,math.radians(.75))
        stopping=bool(a.get('remote_stopping',False))
        transitioning=bool(a.get('remote_reference_transition',False))
        if transitioning:candidate=old_i
        if stopping:
            # Remove driving trim smoothly while braking to zero speed;
            # do not keep building a new bias during this handover.
            candidate=old_i*math.exp(-dt/.20)
            if abs(candidate)<1e-9:candidate=0.
        p_term=plan['speed_kp_rad_per_m_s']*error_v
        requested=p_term+candidate
        pitch_limit=math.radians(plan['speed_pitch_reference_limit_deg'])
        # Do not integrate further into a saturated body request or pitch cap.
        # Opposing error can always unwind the stored remote bias.
        growing=abs(candidate)>abs(old_i) and candidate*old_i>=0
        blocked=a.get('remote_body_limited',False) or (abs(requested)>pitch_limit and requested*error_v>0)
        if not (blocked and growing):self.remote_speed_integral_rad=candidate
        desired=clip(math.degrees(p_term+self.remote_speed_integral_rad),
                     plan['speed_pitch_reference_limit_deg'])
        reference=previous_reference+clip(desired-previous_reference,
                                         plan['speed_pitch_reference_slew_dps']*dt)
        reference=clip(reference,plan['speed_pitch_reference_limit_deg'])
        error=a.get('pitch_error_deg',a['pitch_deg'])-reference
        result=ground_command(dict(a,pitch_error_deg=error),speeds,plan)
        self.pitch_reference_deg=reference
        a['velocity_hold'].update(target_velocity_m_s=target,
            desired_pitch_reference_deg=desired,pitch_reference_deg=reference,
            effective_pitch_error_deg=error,remote_driving_reference=True,
            remote_speed_integral_deg=math.degrees(self.remote_speed_integral_rad),
            remote_speed_integral_blocked=bool(blocked and growing),
            remote_speed_integral_held_for_transition=bool(transitioning and not stopping))
        return result

class RemoteDriveController(NativeDampingController):
    def __init__(self,channel,keys):self.keys=keys;super().__init__(channel)
    def reset(self):
        super().reset();self.remote_gate=False;self.remote_v=0.;self.remote_turn=0.
        self.speed_reference=RemoteVelocityReference();self.drive_profile=DriveVelocityProfile()
        self.remote_started=False;self.remote_expected_turn_rad=0.;self.remote_heading_start=None;self.remote_status={}
        self.remote_turn_integral_nm=0.;self.remote_last_common_nm=0.;self.remote_previous_turn_sign=0
        self.remote_stopping=False;self.remote_stop_settle_s=0.
    def __call__(self,a,speeds,plan=PLAN):
        dt=a['dt'];finite(dt)
        if not 0<dt<=plan['loop_gap_s']:raise Fault('remote_invalid_dt')
        row=self.keys.read(a['t'])
        if row[1] and not row[2] and row[3]==0:self.remote_gate=True
        forward,right=(row[4],row[5]) if self.remote_gate else (0,0)
        target_v=.12*forward;target_turn=4.0*right
        old_v,old_turn=self.remote_v,self.remote_turn
        self.remote_v=self.drive_profile.update(target_v,dt)
        self.remote_turn+=clip(target_turn-self.remote_turn,6.*dt)
        p=a.get('wheel_position_forward_rad',{})
        if set(p)!={0,1}:raise Fault('remote_requires_encoders')
        finite(*p.values())
        position=plan['nominal_wheel_radius_m']*(p[0]+p[1])/2;difference=p[0]-p[1]
        if self.remote_heading_start is None:self.remote_heading_start=difference
        # A turn commands zero mean forward velocity, independently of the
        # differential rate. Never keep chasing an old pre-turn position.
        if self.remote_v or old_v or self.remote_turn or old_turn:
            self.position_origin=position+self.remote_v/plan['position_speed_kp_per_s']
            a['remote_velocity_target_m_s']=self.remote_v
            # Brake trim from key release, not only after the shaped reference
            # reaches zero; avoid integrating a changing acceleration target.
            a['remote_stopping']=forward==0
            a['remote_reference_transition']=abs(target_v-self.remote_v)>.01
            a['remote_body_limited']=self.previous_limited or abs(self.remote_last_common_nm)>=plan['predicted_net_torque_limit_nm']-1e-9
            self.remote_started=True
            self.remote_stopping=True;self.remote_stop_settle_s=0.
        elif self.remote_stopping:
            # A zero reference starts braking, not instantaneous physical
            # stopping. Capture the location only after the measured speed
            # settles, so position return cannot pull back to a premature
            # release point. This preserves the idle PID and its state.
            self.position_origin=position
            a['remote_velocity_target_m_s']=0.
            a['remote_stopping']=True
            raw_mean=plan['nominal_wheel_radius_m']*(speeds[0]+speeds[1])/2
            settled=(abs(self.speed_reference.filtered_velocity)<.01 and
                     abs(raw_mean)<.015 and abs(a['pitch_rate_dps'])<10.)
            self.remote_stop_settle_s=self.remote_stop_settle_s+dt if settled else 0.
            if self.remote_stop_settle_s>=.30:self.remote_stopping=False
        if self.remote_turn or old_turn:
            if old_turn==0 or self.heading_origin is None:
                self.heading_origin=difference
                self.remote_expected_turn_rad=difference-self.remote_heading_start
            self.heading_origin+=self.remote_turn*dt
            self.heading_origin=difference+clip(self.heading_origin-difference,.35)
            self.remote_expected_turn_rad+=self.remote_turn*dt
            if self.remote_turn==0:
                self.heading_origin=difference
                self.remote_expected_turn_rad=difference-self.remote_heading_start
            self.remote_started=True
        self.remote_status=dict(input_reason=row[6],connected=row[1],held_mask=row[3],
            gate_open=self.remote_gate,forward_key=forward,right_key=right,
            commanded_velocity_m_s=self.remote_v,commanded_wheel_difference_rad_s=self.remote_turn,
            expected_turn_difference_rad=self.remote_expected_turn_rad,
            stopping_before_position_hold=self.remote_stopping,
            stop_settle_s=self.remote_stop_settle_s,
            drive_profile_lead_m_s=self.drive_profile.lead,
            forward_reference_released=forward==0,
            scope='nominal reference, not measured floor speed or calibrated yaw',
            input_worker=self.keys.diagnostics.copy(),input_age_s=max(0.,a['t']-self.keys.value[0]))
        a['remote_drive']=self.remote_status.copy()
        return super().__call__(a,speeds,plan)
    def adjust_position_reference(self,attitude,speeds,plan):
        # Only after an operator drive/turn has completed braking. Keep the
        # original no-input standing baseline and all active-drive targets.
        if not self.remote_started or 'remote_velocity_target_m_s' in attitude:
            return
        info=attitude['position_hold'];error=info['relative_error_proxy_m']
        finite(error)
        effective_error=math.copysign(max(0.,abs(error)-.020),error)
        target=clip(-plan['position_speed_kp_per_s']*effective_error,
                    plan['position_speed_limit_m_s'])
        attitude['position_velocity_target_m_s']=target
        info.update(target_velocity_m_s=target,post_drive_tolerance_m=.020,
                    effective_error_proxy_m=effective_error,
                    scope='post_drive_nominal_encoder_position_tolerance_not_motor_or_balance_deadband')
        self.remote_status.update(post_drive_position_tolerance_m=.020,
                                  position_target_velocity_m_s=target)
        attitude['remote_drive'].update(self.remote_status)

    def net_torque_requests(self,common,speeds,attitude,plan):
        super().net_torque_requests(common,speeds,attitude,plan)
        info=attitude['wheel_sync']
        # Active turning uses target-minus-measured rate feedback with pitch priority.
        # Neutral sync and common pitch stay unchanged; turn margin grows within NET.
        turning=self.remote_turn!=0.
        rate_kp=.10 if turning else plan['sync_kp_nm_per_rad_s']
        margin=(max(0.,min(.08,plan['predicted_net_torque_limit_nm']-abs(common)))
                if turning else info['available_margin_nm'])
        rate_feedforward=rate_kp*self.remote_turn
        rate_term=rate_kp*self.filtered_difference
        turn_sign=1 if self.remote_turn>0 else -1 if self.remote_turn<0 else 0
        if turn_sign!=self.remote_previous_turn_sign:self.remote_turn_integral_nm=0.
        self.remote_previous_turn_sign=turn_sign
        rate_error=self.remote_turn+self.filtered_difference
        old_i=self.remote_turn_integral_nm
        candidate=clip(old_i+.08*rate_error*attitude['dt'],.020) if turning else 0.
        base=info['position_term_nm']+rate_term+rate_feedforward
        # Conditional integration preserves pitch priority and the original
        # per-wheel total NET limit; it cannot reserve extra actuator torque.
        saturated=abs(base+candidate)>margin and (base+candidate)*rate_error>0
        growing=abs(candidate)>abs(old_i) and candidate*old_i>=0
        if not (saturated and growing):self.remote_turn_integral_nm=candidate
        correction=clip(base+self.remote_turn_integral_nm,margin)
        self.remote_last_common_nm=common
        self.remote_status.update(measured_left_forward_rad_s=speeds[0],
            measured_right_forward_rad_s=speeds[1],
            measured_left_minus_right_rad_s=speeds[0]-speeds[1],
            filtered_left_minus_right_rad_s=-self.filtered_difference)
        if 'remote_drive' in attitude:attitude['remote_drive'].update(self.remote_status)
        info.update(remote_rate_feedforward_nm=rate_feedforward,correction_nm=correction,
                    rate_term_nm=rate_term,available_margin_nm=margin,
                    remote_turn_active=turning,remote_turn_rate_kp=rate_kp,
                    remote_rate_target_left_minus_right_rad_s=self.remote_turn,
                    remote_turn_integral_nm=self.remote_turn_integral_nm,
                    remote_turn_integral_blocked=bool(saturated and growing))
        return {0:common+correction,1:common-correction}

    def extra_telemetry(self,sample):
        return dict(super().extra_telemetry(sample),remote_drive=self.remote_status.copy())

class RemoteTravel(HoldTravel):
    def __init__(self,rows,signs,plan,controller):
        if plan['net_rolling_limit_m'] is not None or plan['rolling_path_limit_m'] is not None:
            raise Fault('remote_distance_policy_not_explicit')
        super().__init__(rows,signs,plan);self.controller=controller
    def update(self,mid,row):
        position=row['position_rad'];finite(position)
        radius=self.plan['nominal_wheel_radius_m']
        self.path[mid]+=abs(position-self.previous[mid])*radius
        self.offset[mid]=(position-self.origins[mid])*self.signs[mid]*radius;self.previous[mid]=position
        finite(self.path[mid],self.offset[mid])
        error=self.offset[0]-self.offset[1]-radius*self.controller.remote_expected_turn_rad
        if abs(error)>=self.plan['differential_rolling_limit_m']:raise Fault('differential_turn_tracking_stop')
    def snapshot(self):
        r=super().snapshot();expected=self.plan['nominal_wheel_radius_m']*self.controller.remote_expected_turn_rad
        return dict(r,expected_differential_m=expected,differential_tracking_error_m=r['differential_offset_m']-expected,
                    distance_stops_enabled=False,differential_tracking_limit_m=self.plan['differential_rolling_limit_m'])

def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv);ch=TuningChannel(gains(PLAN));keys=Keys()
    c=RemoteDriveController(ch,keys);travel=lambda rows,signs,plan:RemoteTravel(rows,signs,plan,c)
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=c,travel_factory=travel,description=__doc__)
    with KeyWorker(keys,{}),LocalTuningServer(ch):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=ch.session,socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=c,travel_factory=travel,description=__doc__)
if __name__=='__main__':raise SystemExit(main())
