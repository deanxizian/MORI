#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""User-requested wheel-speed margin for the finite position-return trial.

Only the wheel-speed stop changes4 to6rad/s after trial12 speed stop from a
near10deg start. This is not a commanded cruise speed. Torque, posture,
temperature, travel, indicator lifecycle and all controller gains stay fixed.
No automatic fault restart; default invocation does no device I/O.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_position_hold import PLAN as BASE,PositionHoldController

PLAN=dict(BASE,name='two_deck_position_speed_margin_v91',wheel_speed_limit_rad_s=6.,
          active_message='POSITION_MARGIN_ACTIVE: 起点回中版补偿已开始，红点亮起。轮速停止线放宽到6rad/s，仍最多30秒、每轮0.12Nm、20度、70度及原位移和通信保护；请只轻扶防倒。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-position-margin',
                      controller=PositionHoldController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
