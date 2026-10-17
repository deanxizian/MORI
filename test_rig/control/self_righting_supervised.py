#!/usr/bin/env python3
"""Finite supervised rise/capture trial, inert without explicit run flags.

The old retired entries stay held. This candidate begins capture before the
old stable-looking gate, and abandons a failed lift BEFORE a hard fault when
inward progress reverses. Normal abandonment uses a limited native-speed
ramp to zero effort. Actual faults still immediately lock both motors.
No automatic retry. Mode 0 is not power isolation. No physical success is
implied by the command replay or tests.
"""
import math
from air_trial import main as trial_main
from attitude import Fault,finite,clip
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from self_righting_trial import SelfRightingController,position_rates
from self_righting_rate_profile import RATE_PROFILE_PLAN
from protocol import RATIO
from velocity_envelope import velocity_targets


PLAN=dict(RATE_PROFILE_PLAN,
    name='first_layer_supervised_recovery_v50_rotational_low_g',duration_s=10.,
    allow_rotating_low_g=True,
    control_phase='supervised_self_righting',
    wheel_speed_limit_rad_s=15.5,rise_wheel_speed_limit_rad_s=15.5,
    rise_speed_target_rad_s=12.5,
    capture_pitch_deg=18.,capture_rate_dps=120.,capture_velocity_m_s=.5,
    capture_blend_s=.3,
    dynamic_imu_phases=('READY','PRE_ROLL','RISING','CAPTURE','ABORT_BRAKE','ABORT_RELEASE'),
    abort_progress_loss_deg=2.,abort_outward_rate_dps=30.,abort_confirm_s=.02,
    abort_inward_rate_floor_dps=60.,abort_fading_min_pitch_deg=40.,
    abort_before_capture_s=3.,abort_speed_trigger_rad_s=14.,
    abort_no_progress_s=1.4,abort_net_reserve_trigger_m=.10,
    abort_decel_rad_s2=15.,abort_native_kd_nm_per_rad_s=.1,
    abort_target_limit_rad_s=14.5,
    active_message='SUPERVISED_SELF_RIGHTING_ACTIVE: 新的单次起身开始，最多 10 秒；提前接管并在进展反转时减速退出。净目标最多 0.35 Nm，轮速软目标 12.5、独立线 15.5 rad/s，70°C 及传感器/通信/行程异常立即停止；不自动重试。')
PLAN.pop('motion_hold_reason',None)
PLAN['motion_hold_reason']='trial33_overturn: retired launch; physical inspection/reset and successor review required'


class SupervisedRecovery(SelfRightingController):
    def reset(self):
        super().reset()
        self.abort_reason=None;self.abort_begin=None;self.reversal_since=None
        self.abort_initial=None;self.abort_targets=None;self.abort_previous=None
        self.abort_positions=None;self.abort_feedback_times=None;self.abort_still_since=None;self.abort_zero=False
        self.last_commands={0:0.,1:0.}
        self.peak_inward_rate=0.

    def validate_arm(self,a,speeds,plan):
        super().validate_arm(a,speeds,plan)
        values=[plan[k] for k in ('abort_progress_loss_deg','abort_outward_rate_dps','abort_confirm_s',
            'abort_before_capture_s','abort_speed_trigger_rad_s','abort_decel_rad_s2',
            'abort_native_kd_nm_per_rad_s','abort_target_limit_rad_s',
            'abort_inward_rate_floor_dps','abort_fading_min_pitch_deg')]
        finite(*values)
        loss,rate,confirm,deadline,trigger,decel,kd,target,floor,far=values
        if not (0.<loss<=3. and 0.<rate<=60. and .01<=confirm<=.03 and
            0.<deadline<plan['rise_timeout_s'] and 0.<trigger<target<plan['wheel_speed_limit_rad_s'] and
            0.<decel<=15. and 0.<kd<=.15 and 0.<floor<120. and
            plan['capture_pitch_deg']<far<plan['arm_pitch_min_deg']):raise Fault('invalid_supervised_abort_plan')

    def start_abort(self,reason,a,speeds,plan):
        # This is a planned exit from otherwise healthy control, not recovery
        # from an exception, a hard stop, a sensor failure or a latched fault.
        if self.fault or self.abort_reason:raise Fault('abort_reentry_not_allowed')
        self.abort_reason=reason;self.abort_begin=a['t']
        step=RATIO**2/128000000
        old_kd=math.floor(self.applied_damping/step)*step
        new_kd=math.floor(plan['abort_native_kd_nm_per_rad_s']/step)*step
        limit=plan['abort_target_limit_rad_s']
        net=({m:old_kd*(self.velocity_targets[m]-speeds[m]) for m in (0,1)}
             if plan.get('native_velocity_control') else
             {m:self.last_commands[m]-old_kd*speeds[m] for m in (0,1)})
        self.abort_initial={m:clip(speeds[m]+net[m]/new_kd,limit) for m in (0,1)}
        self.abort_targets=self.abort_initial.copy()
        self.abort_previous=a['t'];self.abort_positions=a['wheel_position_forward_rad'].copy()
        self.abort_feedback_times=(a['wheel_feedback_received_monotonic'].copy() if plan.get('use_wheel_feedback_timestamps',False) else None)
        self.transition('ABORT_BRAKE',a)

    def update(self,a,speeds,plan):
        if self.abort_reason:return self.brake(a,speeds,plan)
        if self.phase=='RISING':
            direction=1. if self.start_pitch>0. else -1.
            self.peak_inward_rate=max(self.peak_inward_rate,-direction*a['pitch_rate_dps'])
            progress=abs(self.start_pitch)-direction*a['pitch_deg']
            reversal=(self.best_progress>=5. and self.best_progress-progress>=plan['abort_progress_loss_deg']
                      and direction*a['pitch_rate_dps']>=plan['abort_outward_rate_dps'])
            self.reversal_since=(a['t'] if self.reversal_since is None else self.reversal_since) if reversal else None
            reason=None
            if (plan.get('abort_on_fading_momentum',True) and
                self.best_progress>=10. and self.peak_inward_rate>=120. and
                -direction*a['pitch_rate_dps']<=plan['abort_inward_rate_floor_dps'] and
                abs(a['pitch_deg'])>plan['abort_fading_min_pitch_deg'] and
                max(map(abs,speeds.values()))>=8.):
                reason='inward_momentum_fading_far_from_capture'
            elif self.reversal_since is not None and a['t']-self.reversal_since>=plan['abort_confirm_s']:
                reason='lift_progress_reversed'
            elif a['t']-self.rise_begin>=plan['abort_before_capture_s']:
                reason='capture_not_reached_before_deadline'
            elif (a['t']-self.rise_begin>=plan['abort_no_progress_s'] and
                  self.best_progress<plan['rise_min_progress_deg']):
                reason='no_progress_before_hard_timeout'
            elif max(abs(a['wheel_position_forward_rad'][m]-self.origins[m]) for m in (0,1))*plan['nominal_wheel_radius_m']>=plan['abort_net_reserve_trigger_m']:
                reason='travel_reserve_for_normal_exit'
            elif ((max(direction*plan.get('rise_polarity',1)*v for v in speeds.values())
                    if plan.get('abort_lift_direction_speed_only',False) else max(map(abs,speeds.values())))
                    >=plan['abort_speed_trigger_rad_s'] and abs(a['pitch_deg'])>plan['capture_pitch_deg']):
                reason='wheel_headroom_low_before_capture'
            if reason:
                # Apply the same hard guards before entering normal exit.
                ground_command(a,speeds,dict(plan,pitch_rate_limit_dps=plan['rise_pitch_rate_limit_dps']))
                self.start_abort(reason,a,speeds,plan)
                return self.brake(a,speeds,plan)
        commands=super().update(a,speeds,plan)
        self.last_commands=commands.copy()
        return commands

    def brake(self,a,speeds,plan):
        ground_command(a,speeds,dict(plan,pitch_rate_limit_dps=plan['rise_pitch_rate_limit_dps']))
        if tuple(sorted(plan.items()))!=self.config:raise Fault('self_righting_parameters_changed')
        pos=a['wheel_position_forward_rad'];finite(a['t'],a['dt'],*pos.values())
        dt=a['t']-self.abort_previous
        if dt==0.:dt=a['dt']
        if not .001<=dt<=plan['loop_gap_s']:raise Fault('supervised_abort_sample_gap')
        rates,new_times=position_rates(a,speeds,
            None if a['t']==self.abort_previous else self.abort_positions,
            self.abort_feedback_times,dt,plan)
        self.abort_feedback_times=new_times
        elapsed=a['t']-self.abort_begin
        desired={m:math.copysign(max(0.,abs(self.abort_initial[m])-plan['abort_decel_rad_s2']*elapsed),self.abort_initial[m]) for m in (0,1)}
        if self.abort_zero:
            self.abort_targets={0:0.,1:0.};self.applied_damping=0.
            info=dict(scope='zero FF/Kp/Kd after planned deceleration; no automatic restart')
        else:
            p=dict(plan,velocity_native_kd_nm_per_rad_s=plan['abort_native_kd_nm_per_rad_s'],
                velocity_target_limit_rad_s=plan['abort_target_limit_rad_s'],velocity_target_slew_rad_s2=200.)
            kd=p['velocity_native_kd_nm_per_rad_s']
            requests={m:kd*(desired[m]-speeds[m]) for m in (0,1)}
            self.abort_targets,info=velocity_targets(requests,speeds,rates,self.abort_targets,dt,p)
            self.applied_damping=kd
            still=(max(map(abs,desired.values()))==0. and max(map(abs,speeds.values()))<.1)
            self.abort_still_since=(a['t'] if self.abort_still_since is None else self.abort_still_since) if still else None
            if self.abort_still_since is not None and a['t']-self.abort_still_since>=.05:
                self.abort_zero=True;self.abort_targets={0:0.,1:0.};self.applied_damping=0.
                self.transition('ABORT_RELEASE',a)
        self.abort_previous=a['t'];self.abort_positions=pos.copy()
        a['self_righting']=dict(phase=self.phase,elapsed_s=a['t']-self.begin,
            planned_abort_reason=self.abort_reason,abort_elapsed_s=elapsed,
            initial_velocity_targets_rad_s=self.abort_initial.copy(),velocity_targets_forward_rad_s=self.abort_targets.copy(),
            best_progress_deg=self.best_progress,native_velocity_budget=info,
            stable_s=0.,scope='controlled unsuccessful exit; not successful self-righting')
        return {0:0.,1:0.}

    def motor_plan(self,plan):
        if not self.abort_reason:return super().motor_plan(plan)
        return dict(plan,native_velocity_control=True,native_wheel_damping_nm_per_rad_s=self.applied_damping,
            velocity_target_limit_rad_s=plan['abort_target_limit_rad_s'],feedforward_torque_limit_nm=0.,
            velocity_targets_forward_rad_s=self.abort_targets.copy())

    def finish(self):
        if self.abort_reason:raise Fault('planned_abort_'+self.abort_reason)
        super().finish()

    def summary(self):
        return dict(super().summary(),planned_abort_reason=self.abort_reason,
            normal_exit_reached_zero_effort=self.abort_zero)


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-supervised-self-righting',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
