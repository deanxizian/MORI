#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite operator-held loaded speed check, never autonomous balancing.

Reuse the exercised v112 native velocity packet/allocation and the existing
air_trial zero-arm, IMU, raw feedback, cue and final-stop harness. Both
wheels receive one fixed signed ramp/plateau, pause, reverse and stop. No
attitude/speed/position host PID, gain learning, friction aid or auto rearm.
The operator must hold the body upright while allowing short floor travel.
Sampled predicted NET is not a hardware torque clamp or a friction measure.
"""
from dataclasses import replace
import math

from air_trial import main as trial_main
from attitude import Fault,finite
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from two_deck_live_quiet_baseline import PLAN as BASE
from wheel_rate_probe import NativeVelocityCommand,packet


START='--run-ground-constant-rate-probe'
PLAN=dict(BASE,name='ground_constant_rate_probe_held_cue_v158',duration_s=9.,
    control_phase='ground_constant_rate_probe',allow_live_tuning=False,
    status='EXPERIMENTAL_OPERATOR_HELD_LOADED_RATE_DIAGNOSTIC',
    control_method='native_velocity_p',half_hour_live_session=False,
    kp_nm_per_rad=0.,kd_nm_per_rad_s=0.,
    feedforward_torque_limit_nm=.08,predicted_net_torque_limit_nm=.08,
    estimated_torque_limit_nm=.12,active_torque_feedback_guard=False,
    wheel_speed_limit_rad_s=.6,temperature_limit_c=70,
    pitch_limit_deg=12.,roll_limit_deg=8.,pitch_rate_limit_dps=80.,
    net_rolling_limit_m=.04,rolling_path_limit_m=.08,differential_rolling_limit_m=.01,
    constant_rate_probe=True,
    operator_held_diagnostic=True,
    wait_upright_message='WAIT_UPRIGHT: 两轮停止。固定速度诊断需要你始终扶稳车身保持直立，两轮着地且可小幅滚动，不是自平衡。',
    pose_ready_message='POSE_READY: 直立窗口通过，正在确认零速模式；请继续扶稳车身，诊断期间不要松手。',
    active_message='HELD_CONSTANT_RATE_ACTIVE: 扶稳诊断开始；红点始终熄灭，没有平衡开始音，绝不能松手。请扶住车身保持直立，让整车能小幅滚动。双轮前进4秒、停半秒、后退4秒，再停；目标0.20rad/s（名义轮缘8毫米每秒），预测NET最多0.08Nm，0.6rad/s、净4厘米/累计8厘米、12度、70度或异常停止。')


def desired_rate(elapsed):
    finite(elapsed)
    if elapsed<0:raise Fault('negative_constant_rate_time')
    if elapsed<4.:stage,local,sign='forward',elapsed,1.
    elif elapsed<4.5:return 'pause',0.
    elif elapsed<8.5:stage,local,sign='reverse',elapsed-4.5,-1.
    else:return 'final_zero',0.
    fraction=max(0.,min(1.,local/.4,(4.-local)/.4))
    return stage,sign*.20*fraction


class ConstantRateProbe:
    def __init__(self):
        self.ever_active=False
        self.reset()

    def reset(self):
        if self.ever_active:raise Fault('constant_rate_cannot_reset_after_active')
        self.begin=self.previous=self.configuration=None
        self.allocations={};self.fault=None;self.checked_stages=set()
        self.output_previous={};self.output_offset={0:0.,1:0.}
        self.command=NativeVelocityCommand()

    def validate_arm(self,a,speeds,plan):
        if plan.get('constant_rate_probe') is not True or plan['duration_s']!=9.:
            raise Fault('constant_rate_explicit_profile_required')
        if (plan['wheel_speed_limit_rad_s']!=.6 or plan['predicted_net_torque_limit_nm']!=.08
                or plan['temperature_limit_c']!=70 or plan['active_torque_feedback_guard'] is not False):
            raise Fault('constant_rate_profile_changed')
        ground_command(a,speeds,plan)
        if set(speeds)!={0,1}:raise Fault('constant_rate_requires_both_wheels')

    def __call__(self,a,speeds,plan=PLAN):
        if self.fault:raise Fault('constant_rate_fault_latched')
        try:return self.update(a,speeds,plan)
        except Exception as exc:
            self.fault=str(exc);raise

    def update(self,a,speeds,plan):
        self.validate_arm(a,speeds,plan)
        t=a['t'];dt=a['dt'] if self.previous is None else t-self.previous
        finite(t,dt)
        if not .001<=dt<=plan['loop_gap_s']:raise Fault('constant_rate_sample_gap')
        if self.begin is None:
            self.begin=t;self.configuration=plan.copy();self.ever_active=True
        elif self.configuration!=plan:raise Fault('constant_rate_configuration_changed')
        stage,target=desired_rate(t-self.begin)
        if t-self.begin>9.025:raise Fault('constant_rate_duration_overrun')
        self.allocations={};info={}
        for mid in (0,1):
            allocation,detail=self.command.update(target,speeds[mid],dt)
            self.allocations[mid]=allocation;info[mid]=detail
        a['constant_rate_probe']=dict(stage=stage,elapsed_s=t-self.begin,
            target_forward_rad_s=target,per_wheel=info,
            scope='Operator-held fixed native wheel speed, no host balance PID; sampled NET only.')
        self.previous=t
        return {0:0.,1:0.}

    def allocated_torque_packet(self,mid,sign,value,plan):
        if value!=0. or mid not in self.allocations or sign not in (-1,1):
            raise Fault('constant_rate_packet_mismatch')
        allocation=self.allocations[mid]
        return packet(mid,replace(allocation,velocity_raw=allocation.velocity_raw*sign))

    def observe_pair(self,sample):
        self.checked_stages.add(sample['attitude']['constant_rate_probe']['stage'])
        for mid,sign in ((0,1),(1,-1)):
            angle=sample['wheels'][mid]['feedback']['absolute_output_rad'];finite(angle)
            if not 0<=angle<math.tau:raise Fault('constant_rate_output_angle_invalid')
            if mid in self.output_previous:
                delta=sign*((angle-self.output_previous[mid]+math.pi)%math.tau-math.pi)*.04
                self.output_offset[mid]+=delta
            self.output_previous[mid]=angle
            # Independent output samples are noisy. Their absolute-increment
            # sum is not a usable path measure. The inherited high-resolution
            # rotor ledger owns the cumulative8cm guard; this adds net4cm.
            if abs(self.output_offset[mid])>=.04:
                raise Fault('constant_rate_independent_output_travel_stop')

    def finish(self):
        if self.checked_stages!={'forward','pause','reverse','final_zero'}:
            raise Fault('constant_rate_incomplete_sequence')

    def summary(self):
        return dict(checked_stages=sorted(self.checked_stages),fault=self.fault,
            independent_output_offset_m=self.output_offset.copy(),
            balanced_operation='NOT_APPLICABLE',loaded_smoothness='NOT_TESTED',automatic_rearm=False)


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag=START,controller=ConstantRateProbe(),
                      travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
