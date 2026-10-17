#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite restrained recovery-window comparison, not a self-righting routine.

Same v13 ArduPilot pitch PID and torque bounds. Reduced native zero-speed
damping and an explicitly enlarged angle/speed/travel window are experimental
responses to trial 18. Default invocation opens no hardware; a new onsite
unlock is required. No start from a fallen pose, automatic rearm or service.
"""
from air_trial import main as trial_main
from ground_ardupilot_balance import ARDUPILOT_PLAN,ArduPilotBalanceController
from ground_hold_trial import HoldTravel


RECOVERY_PLAN=dict(
    ARDUPILOT_PLAN,
    name='restrained_ardupilot_recovery_window_v14',
    native_wheel_damping_nm_per_rad_s=.025,
    pitch_limit_deg=30.,
    wheel_speed_limit_rad_s=4.,
    net_rolling_limit_m=.30,
    rolling_path_limit_m=1.0,
    active_message='RESTRAINED_GROUND_ACTIVE: 降低轮速阻尼、扩大恢复窗口的对照开始，最多 15 秒；请轻扶防倒，让小车自行纠偏。前馈仍为 0.12 Nm，30 度、约 229 度/秒、70 度或原故障条件停止；不支持倒地后自动重新启动。',
)


def main(argv=None):
    return trial_main(argv,plan=RECOVERY_PLAN,
                      start_flag='--run-restrained-recovery-window',
                      controller=ArduPilotBalanceController(),
                      travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
