#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite, explicitly invoked lift-authority comparison. No I/O by default.

The 0.35 Nm net target is an experimental output-side, ideal-ratio command;
it is not measured shaft torque. Retains the finite stop/temperature/speed/
impact/travel guards. Vendor stall torque is not a continuous rating.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_trial import SELF_RIGHT_PLAN, SelfRightingController


LIFT_PLAN = dict(
    SELF_RIGHT_PLAN,
    name='first_layer_self_righting_v42_early_speed_governor',
    post_stop_observation_s=2.,
    imu_bandwidth_divisor=4,
    rise_pitch_rate_limit_dps=400.,
    native_wheel_damping_nm_per_rad_s=.025,
    pre_roll_native_wheel_damping_nm_per_rad_s=.030,
    rise_native_wheel_damping_nm_per_rad_s=.025,
    feedforward_torque_limit_nm=.50,
    rise_feedforward_torque_limit_nm=.60,
    control_torque_limit_nm=.35,
    predicted_net_torque_limit_nm=.35,
    estimated_torque_limit_nm=.42,
    pre_roll_duration_s=.40,
    pre_roll_ramp_s=.15,
    pre_roll_torque_nm=.30,
    pre_roll_target_rad_s=7.5,
    pre_roll_speed_limit_rad_s=11.5,
    pre_roll_travel_limit_m=.10,
    rise_ramp_s=.08,
    rise_kp_nm_per_rad=.40,
    rise_polarity=1,
    rise_dynamic_imu=True,
    wheel_speed_limit_rad_s=12.,
    rise_wheel_speed_limit_rad_s=15.5,
    rise_speed_target_rad_s=11.,
    rise_speed_gain_nm_per_rad_s=.1,
    rise_speed_position_guard=True,
    rise_compensate_native_damping=True,
    pre_roll_compensate_native_damping=True,
    active_message='SELF_RIGHTING_ACTIVE: 提前限速对照现在开始，最多 10 秒；轮速软目标 11 rad/s，同时看速度反馈和位置差分提前减小驱动。独立停止线仍为 15.5 rad/s、70°C，净目标最多 0.35 Nm；故障立即锁定两轮，随后继续被动记录姿态，不自动重试。',
)


def main(argv=None):
    return trial_main(argv, plan=LIFT_PLAN, start_flag='--run-single-self-righting',
                      controller=SelfRightingController(), travel_factory=HoldTravel,
                      description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
