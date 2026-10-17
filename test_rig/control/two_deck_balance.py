#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Upright-only, ten-second guarded balance baseline for the two-deck demo.

User reports about 650 g, unchanged BMI323 pose and wheel interfaces. This
reuses the previously exercised ArduPilot pitch PID port without importing a
swing-up controller. Gains are experimental, not identified for the new load.
Default invocation is inert; a fresh explicit launch allows one finite run.
"""
from air_trial import main as trial_main
from ground_ardupilot_balance import ArduPilotBalanceController
from ground_ardupilot_rate_window import RATE_PLAN
from ground_hold_trial import HoldTravel


PLAN = dict(
    RATE_PLAN,
    motion_hold_reason='Baseline01 stopped on raw lateral-acceleration angle; retired pending reviewed fused-roll successor.',
    name='two_deck_upright_baseline_v79',
    duration_s=10.,
    control_phase='ground_two_deck_pid',
    imu_odr_hz=200,
    imu_bandwidth_divisor=4,
    post_stop_observation_s=2.,
    pitch_limit_deg=20.,
    plant_scope='Two decks, CAM and display installed; about650g user estimate, COM/inertia unmeasured',
    wait_upright_message='WAIT_UPRIGHT: 两轮停止；请大致扶正并轻扶防倒，等待半秒姿态窗口。不会从躺姿启动。',
    pose_ready_message='POSE_READY: 直立姿态窗口已通过，正在确认零速接管；请继续防倒。',
    active_message='TWO_DECK_BALANCE_ACTIVE: 两轮平衡补偿现在开始，最多10秒。请只轻扶防倒，不要主动来回晃；到时或保护停机后请接住。单轮前馈上限0.12Nm，轮速4rad/s、俯仰20度、70度及原转量/通信条件停止，不自动重试。',
)


def main(argv=None):
    return trial_main(
        argv, plan=PLAN, start_flag='--run-two-deck-balance',
        controller=ArduPilotBalanceController(), travel_factory=HoldTravel,
        description=__doc__,
    )


if __name__ == '__main__':
    raise SystemExit(main())
