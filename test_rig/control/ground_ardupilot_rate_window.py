#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded rate-window correction after a measured inward recovery stop.

Only the body pitch-rate diagnostic threshold changes, 100 to 200 deg/s.
All v14b actuator commands, gains, temperature, angle, travel and timing
conditions remain unchanged. Default is inert; no automatic fault rearm.
"""
from air_trial import main as trial_main
from ground_ardupilot_balance import ArduPilotBalanceController
from ground_ardupilot_observe_long import LONG_PLAN
from ground_hold_trial import HoldTravel

RATE_PLAN=dict(
    LONG_PLAN,name='restrained_ardupilot_recovery_rate_window_v15',pitch_rate_limit_dps=200.,
    active_message='RESTRAINED_GROUND_ACTIVE: 60 秒补偿现在开始，可以轻推一次后松开推力，保持防倒。仅机身俯仰转速停止线改为 200 度/秒；30 度、轮速约 229 度/秒、0.12 Nm、70 度和原转量等条件保留。',
)


def main(argv=None):
    return trial_main(argv,plan=RATE_PLAN,
                      start_flag='--run-restrained-recovery-rate-window',
                      controller=ArduPilotBalanceController(),
                      travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
