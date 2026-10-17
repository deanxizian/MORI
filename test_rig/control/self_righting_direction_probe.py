#!/usr/bin/env python3
"""Finite reverse-polarity diagnostic; never a self-righting success claim.

User observed motion towards the fallen side. Compare the opposite common
wheel command against short-time gyro integration, retaining both raw/fused
attitude logs. This does not replace the labelled wheel/IMU calibration or the
standing controller. One explicit invocation, no retry or automatic re-arm.
"""
import math
import argparse

from air_trial import main as trial_main
from attitude import Fault,finite
from ground_hold_trial import HoldTravel
from ground_trial import ground_command
from self_righting_lift_trial import LIFT_PLAN
from self_righting_trial import SelfRightingController,budget,govern_rise_speed


PROBE_PLAN=dict(LIFT_PLAN,
    name='first_layer_v26_reverse_direction_probe',duration_s=.8,
    pre_roll_duration_s=0.,
    control_phase='self_righting_direction_probe',probe_direction=-1,
    probe_torque_nm=.12,probe_ramp_s=.3,probe_gyro_travel_deg=5.,
    native_wheel_damping_nm_per_rad_s=.010,
    feedforward_torque_limit_nm=.20,control_torque_limit_nm=.12,
    predicted_net_torque_limit_nm=.12,estimated_torque_limit_nm=.16,
    rise_speed_target_rad_s=3.,rise_speed_gain_nm_per_rad_s=.08,
    wheel_speed_limit_rad_s=6.,pitch_rate_limit_dps=100.,
    net_rolling_limit_m=.05,rolling_path_limit_m=.08,
    differential_rolling_limit_m=.02,
    active_message='REVERSE_DIRECTION_PROBE: 现在短时反向探测，最多 0.8 秒、合成目标 0.12 Nm、前馈最多 0.20 Nm；轮速软目标 3 rad/s，6 rad/s、转角 5°、70°C 或异常停止。')


class DirectionProbe:
    def __init__(self):
        self.begin=self.previous=self.start_pitch=None
        self.gyro_delta=0.;self.gyro_path=0.;self.fault=None
        self.best_progress=0.;self.samples=0
        self.probe_direction=None

    def validate_arm(self,a,speeds,plan):
        SelfRightingController().validate_arm(a,speeds,plan)

    def __call__(self,a,speeds,plan=PROBE_PLAN):
        if self.fault is not None:raise Fault('direction_probe_fault_latched_'+self.fault)
        try:return self.update(a,speeds,plan)
        except Exception as exc:
            self.fault=str(exc) or type(exc).__name__
            raise

    def update(self,a,speeds,plan):
        ground_command(a,speeds,plan)
        finite(a['t'],a['dt'])
        if plan['probe_direction'] not in (-1,1):raise Fault('invalid_probe_direction')
        if self.probe_direction is not None and self.probe_direction!=plan['probe_direction']:
            raise Fault('probe_direction_changed')
        self.probe_direction=plan['probe_direction']
        if self.begin is None:
            self.validate_arm(a,speeds,plan)
            self.begin=self.previous=a['t'];self.start_pitch=a['pitch_deg']
        else:
            dt=a['t']-self.previous
            if not .001<=dt<=plan['loop_gap_s']:raise Fault('direction_probe_sample_gap')
            turn=a['pitch_rate_dps']*dt
            self.gyro_delta+=turn;self.gyro_path+=abs(turn);self.previous=a['t']
        direction=math.copysign(1.,self.start_pitch)
        self.best_progress=max(self.best_progress,-direction*self.gyro_delta)
        if self.gyro_path>=plan['probe_gyro_travel_deg']:raise Fault('direction_probe_gyro_travel_stop')
        elapsed=a['t']-self.begin
        if elapsed>plan['duration_s']+plan['loop_gap_s']:raise Fault('direction_probe_duration_exceeded')
        value=plan['probe_direction']*direction*plan['probe_torque_nm']*min(1.,elapsed/plan['probe_ramp_s'])
        requests=govern_rise_speed({0:value,1:value},speeds,plan,0.)
        commands=budget(requests,speeds,plan,1.)
        self.samples+=1
        a['direction_probe']=dict(elapsed_s=elapsed,gyro_delta_deg=self.gyro_delta,
            gyro_path_deg=self.gyro_path,progress_towards_upright_deg=-direction*self.gyro_delta,
            common_request_nm=value,governed_net_request_nm=requests,command_forward_nm=commands)
        return commands

    def summary(self):
        return dict(diagnostic='common_wheel_polarity_probe',probe_direction=self.probe_direction,gyro_delta_deg=self.gyro_delta,
            gyro_path_deg=self.gyro_path,best_gyro_progress_deg=self.best_progress,
            fault=self.fault,automatic_rearm=False,physical_self_righting='NOT_TESTED')


def main(argv=None):
    selector=argparse.ArgumentParser(add_help=False)
    selector.add_argument('--polarity',choices=('original','opposite'),default='opposite')
    selected,rest=selector.parse_known_args(argv)
    direction=1 if selected.polarity=='original' else -1
    label='原方向' if direction==1 else '反方向'
    plan=dict(PROBE_PLAN,probe_direction=direction,
        name='first_layer_v26_1_direction_probe_'+selected.polarity,
        active_message=f'DIRECTION_PROBE: 现在按{label}探测，最多 0.8 秒、合成目标 0.12 Nm、前馈最多 0.20 Nm；轮速软目标 3 rad/s，6 rad/s、累计转角 5°、70°C 或异常停止。')
    return trial_main(rest,plan=plan,start_flag='--run-direction-probe',
        controller=DirectionProbe(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
