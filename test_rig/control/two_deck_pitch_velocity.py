#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental pitch-frame correction of the v100 velocity input only.

An axle encoder reports wheel rotation relative to its moving motor case.
For the calibrated common forward sign, absolute wheel rate is relative
shaft rate plus forward body pitch rate. Nominal radius times that rate
still assumes rolling without slip; it is NOT a floor-speed measurement,
an ArduPilot EKF, or a calibrated internal sensor-delay compensation.

The already shadow-tested helper brackets encoder host receive timestamps
between adjacent IMU reads. The first sample uses the legacy raw proxy for
one cycle while building its bracket. Later missing/stale/unbracketed data
raises a fault, never silently falls back. Raw shaft rates still own health
checks, native damping allocation, differential heading and travel guards.
No pitch PID/gain change, friction aid, new authority or automatic rearm.
"""
from air_trial import main as trial_main
from attitude import Fault
from ground_hold_trial import HoldTravel
from ground_velocity_hold import VelocityHoldController
from offline_after24_20261017.pitch_velocity_proxy import PitchVelocityProxy
from two_deck_heading_hold import RelativeHeadingController
from two_deck_speed_damping import PLAN as BASE


PLAN=dict(BASE,name='two_deck_pitch_frame_velocity_v105',
          use_wheel_feedback_timestamps=True,
          use_pitch_corrected_velocity=True,
          control_phase='two_deck_pitch_frame_velocity_pid',
          active_message='PITCH_FRAME_ACTIVE: 补偿已开始，红点亮起，最多30秒。车速估计加入车身俯仰转动，速度P仍为0.40，其他控制参数不变。这轮不推碰，手只防倒；每轮0.12Nm、轮速6rad/s、正负30度、70度及其他停止条件保留。')


class PitchCorrectedVelocityReference(VelocityHoldController):
    def __init__(self):
        super().__init__()
        self.frame_estimator=None
        self.configuration=None

    def velocity_proxy(self,attitude,speeds,plan):
        if (plan.get('use_pitch_corrected_velocity') is not True or
                plan.get('use_wheel_feedback_timestamps') is not True):
            raise Fault('pitch_velocity_requires_explicit_timestamped_opt_in')
        config=(plan['nominal_wheel_radius_m'],plan['loop_gap_s'])
        if self.configuration is not None and config!=self.configuration:
            raise Fault('pitch_velocity_configuration_changed')
        try:
            if self.frame_estimator is None:
                self.frame_estimator=PitchVelocityProxy(radius_m=config[0],
                    max_feedback_age_s=.015,max_gap_s=config[1])
                self.configuration=config
            diagnostic=self.frame_estimator.update(attitude['t'],attitude['pitch_rate_dps'],
                speeds,attitude.get('wheel_feedback_received_monotonic',{}))
        except ValueError as exc:
            raise Fault('pitch_velocity_'+str(exc)) from exc
        proxy=(diagnostic['corrected_proxy_m_s'] if diagnostic['ready']
               else diagnostic['raw_proxy_m_s'])
        attitude['velocity_frame_control']=dict(diagnostic,
            selected_control_proxy_m_s=proxy,
            first_sample_raw_warmup=not diagnostic['ready'],
            internal_sensor_latency_calibrated=False)
        return proxy


class PitchFrameVelocityController(RelativeHeadingController):
    def reset(self):
        super().reset()
        self.speed_reference=PitchCorrectedVelocityReference()


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-pitch-velocity',
                      controller=PitchFrameVelocityController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
