#!/usr/bin/env python3
"""Finite angle-scheduled body damping comparison, inert by default.

Uses v42 torque packets and the same independent speed/torque/IMU limits.
Lower damping above 50 degrees preserves lift acceleration; increased damping
below 20 degrees requests braking before upright. This is experimental tuning,
not a plant-model guarantee. No automatic retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_trial import SelfRightingController
from self_righting_lift_trial import LIFT_PLAN


RATE_PROFILE_PLAN=dict(LIFT_PLAN,
    name='first_layer_self_righting_v44_angle_scheduled_body_damping',
    rise_far_kd_nm_per_rad_s=.030,rise_near_kd_nm_per_rad_s=.120,
    rise_damping_near_pitch_deg=20.,rise_damping_far_pitch_deg=50.,
    active_message='SELF_RIGHTING_ACTIVE: 分段姿态阻尼对照现在开始，最多 10 秒。大倾角少阻尼，接近直立加强阻尼；净目标最多 0.35 Nm、轮速软目标 11 rad/s，15.5 rad/s、70°C 及原异常停止条件保留。故障锁定并记录尾段，无自动重试。')


def main(argv=None):
    return trial_main(argv,plan=RATE_PROFILE_PLAN,start_flag='--run-single-self-righting-rate-profile',
        controller=SelfRightingController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
