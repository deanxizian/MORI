#!/usr/bin/env python3
"""Low-energy stop-mode characterization; not a self-righting attempt.

One 0.6 s or 2 s speed pulse up to 0.8 rad/s at a predicted 0.08 Nm per wheel.
The longer pulse requires zero FF/Kp/Kd release before locking and releases
early when either output reaches 25 degrees. The normal release window is
at least 0.35 s. All actual faults still use the existing immediate
mode-0 stop, with passive IMU recording. No auto retry or fault rearm.
"""
import argparse
import math
from air_trial import main as trial_main
from attitude import Fault,finite
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from self_righting_lift_trial import LIFT_PLAN
from velocity_envelope import velocity_targets


def make_plan(style,pulse_s=.6):
    if style not in ('lock','release'):raise ValueError('invalid_stop_style')
    if pulse_s not in (.6,2.) or (pulse_s==2. and style!='release'):
        raise ValueError('long_probe_requires_release_style')
    p=dict(LIFT_PLAN,name='low_speed_stop_probe_v46_'+style,
        duration_s=pulse_s+(.35 if style=='release' else 0.),control_phase='low_speed_stop_probe',
        pulse_s=pulse_s,pulse_ramp_s=.2,pulse_wheel_angle_limit_deg=25.,stop_style=style,
        kp_nm_per_rad=0.,kd_nm_per_rad_s=0.,
        native_velocity_control=True,velocity_native_kd_nm_per_rad_s=.1,
        velocity_target_limit_rad_s=.8,velocity_target_slew_rad_s2=8.,
        native_wheel_damping_nm_per_rad_s=.1,arm_native_wheel_damping_nm_per_rad_s=.1,
        feedforward_torque_limit_nm=0.,predicted_net_torque_limit_nm=.08,
        estimated_torque_limit_nm=.12,wheel_speed_limit_rad_s=1.5,
        pitch_rate_limit_dps=80.,rolling_path_limit_m=.03,net_rolling_limit_m=.03,
        differential_rolling_limit_m=.01,post_stop_observation_s=2.,
        rise_dynamic_imu=False,
        pose_ready_message='LOW_SPEED_READY: 已确认静止躺姿；倒计时后只做低速转轮对照，不尝试起身。',
        active_message=f'LOW_SPEED_STOP_PROBE_ACTIVE: 低速转轮开始；脉冲最多 {pulse_s} 秒、任一轮达到约 25°即提前卸力，轮速指令最多 0.8 rad/s、预测净目标最多 0.08 Nm。70°C 或异常仍立即锁定；本轮不尝试起身。')
    p.pop('motion_hold_reason',None)
    return p


class StopProbeController:
    def __init__(self):self.reset()
    def reset(self):
        self.begin=self.previous=self.positions=self.start_pitch=None
        self.targets={0:0.,1:0.};self.kd=0.;self.phase='READY';self.fault=None
        self.config=None;self.coast_seen=False
        self.origins=None;self.release_latched=False
        self.release_begin=None;self.release_targets=None

    def validate_arm(self,a,speeds,plan):
        ground_command(a,speeds,dict(plan,native_wheel_damping_nm_per_rad_s=0.))
        if not (75.<=abs(a['pitch_deg'])<=100. and abs(a['roll_deg'])<=5.
                and abs(a['pitch_rate_dps'])<3. and max(map(abs,speeds.values()))<=.1):
            raise Fault('stop_probe_requires_still_lying_pose')
        velocity_targets({0:0.,1:0.},speeds,speeds,{0:0.,1:0.},a['dt'],plan)
        decel=plan.get('normal_decel_s',0.)
        finite(decel)
        if not 0.<=decel<=.2 or (decel and plan['stop_style']!='release'):
            raise Fault('invalid_stop_probe_deceleration')

    def __call__(self,a,speeds,plan):
        if self.fault:raise Fault('stop_probe_fault_latched')
        try:return self.update(a,speeds,plan)
        except Exception as exc:
            self.fault=str(exc);raise

    def update(self,a,speeds,plan):
        ground_command(a,speeds,dict(plan,native_wheel_damping_nm_per_rad_s=0.))
        config=tuple(sorted(plan.items()))
        if self.config is not None and config!=self.config:raise Fault('stop_probe_plan_changed')
        self.config=config
        pos=a.get('wheel_position_forward_rad',{})
        if set(pos)!={0,1}:raise Fault('stop_probe_requires_positions')
        finite(a['t'],a['dt'],*pos.values(),*speeds.values())
        if self.begin is None:
            self.validate_arm(a,speeds,plan)
            self.begin=a['t'];self.start_pitch=a['pitch_deg']
            self.origins=pos.copy()
        dt=a['dt'] if self.previous is None else a['t']-self.previous
        if not .001<=dt<=plan['loop_gap_s']:raise Fault('stop_probe_sample_gap')
        if abs(a['pitch_deg']-self.start_pitch)>3.:raise Fault('stop_probe_body_moved')
        rates=({m:(pos[m]-self.positions[m])/dt for m in (0,1)} if self.positions is not None else speeds.copy())
        elapsed=a['t']-self.begin
        reached=any(abs(pos[m]-self.origins[m])>=math.radians(plan['pulse_wheel_angle_limit_deg']) for m in (0,1))
        self.release_latched|=elapsed>=plan['pulse_s'] or reached
        if not self.release_latched:
            self.phase='LOW_SPEED_PULSE';self.kd=plan['velocity_native_kd_nm_per_rad_s']
            target=plan['velocity_target_limit_rad_s']*min(1.,elapsed/plan['pulse_ramp_s'])
            requests={m:self.kd*(target-speeds[m]) for m in (0,1)}
            self.targets,budget=velocity_targets(requests,speeds,rates,self.targets,dt,plan)
        else:
            if plan['stop_style']!='release':raise Fault('stop_probe_pulse_overrun')
            if self.release_begin is None:
                self.release_begin=a['t'];self.release_targets=self.targets.copy()
            decel=plan.get('normal_decel_s',0.)
            decel_elapsed=a['t']-self.release_begin
            if decel_elapsed<decel:
                self.phase='CONTROLLED_DECELERATION';self.kd=plan['velocity_native_kd_nm_per_rad_s']
                fraction=max(0.,1.-decel_elapsed/decel)
                desired={m:self.release_targets[m]*fraction for m in (0,1)}
                requests={m:self.kd*(desired[m]-speeds[m]) for m in (0,1)}
                decel_plan=dict(plan,velocity_target_slew_rad_s2=max(plan['velocity_target_slew_rad_s2'],
                    max(map(abs,self.release_targets.values()))/decel))
                self.targets,budget=velocity_targets(requests,speeds,rates,self.targets,dt,decel_plan)
            else:
                self.phase='ZERO_TORQUE_OBSERVE';self.kd=0.;self.targets={0:0.,1:0.}
                budget={'scope':'zero FF, Kp and Kd command; gear friction is not removed'}
                self.coast_seen=True
        self.previous=a['t'];self.positions=pos.copy()
        a['stop_probe']=dict(phase=self.phase,elapsed_s=elapsed,targets_forward_rad_s=self.targets.copy(),
            native_kd=self.kd,budget=budget,position_rates_rad_s=rates,
            angle_limit_reached=reached,release_latched=self.release_latched)
        return {0:0.,1:0.}

    def motor_plan(self,plan):
        return dict(plan,native_wheel_damping_nm_per_rad_s=self.kd,
            velocity_targets_forward_rad_s=self.targets.copy())

    def finish(self):
        if dict(self.config)['stop_style']=='release' and not self.coast_seen:
            raise Fault('zero_torque_observation_missing')

    def summary(self):
        return dict(phase=self.phase,fault=self.fault,zero_torque_phase_seen=self.coast_seen,
            automatic_rearm=False,self_righting_attempt=False)


def main(argv=None):
    selector=argparse.ArgumentParser(add_help=False)
    selector.add_argument('--stop-style',choices=('lock','release'),default='release')
    selector.add_argument('--pulse-seconds',type=float,choices=(.6,2.),default=.6)
    options,rest=selector.parse_known_args(argv)
    return trial_main(rest,plan=make_plan(options.stop_style,options.pulse_seconds),start_flag='--run-low-speed-stop-probe',
        controller=StopProbeController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
