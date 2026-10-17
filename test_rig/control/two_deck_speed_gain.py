#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""15s bounded zero-speed reference gain comparison against v93.

Only change existing velocity-reference P0.25to0.50rad/(m/s). Retain50ms LPF,
1deg reference limit,2deg/s slew, unchanged pitchPID/heading/NET output and
all hardware fault/stop lifecycle. No position return, minimum shaping,
wheel-rate PI, automatic rearm, or direct higher torque/speed target.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_speed_response import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController

PLAN=dict(BASE,name='two_deck_zero_speed_reference_gain_v94',
          speed_kp_rad_per_m_s=.50,
          control_phase='two_deck_zero_speed_reference_gain_pid',
          active_message='SPEED_GAIN_ACTIVE: 平衡补偿开始，红点亮起，最多15秒。零速反馈增益提高一倍，目标倾角仍正负1度；每轮FF/净输出预算0.12Nm、轮速6rad/s、20度、70度及原停止保护。请只防倒，先不要推车。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-speed-gain',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
