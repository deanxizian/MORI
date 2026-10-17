#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One-factor comparison after operator-confirmed 30s self-balancing.

Reduce only physical pitch integral gain0.6 to0.15Nm/(rad*s). Keep P/D,
speed reference, heading correction, budgets and every stop guard unchanged.
This tests an oscillation hypothesis, not a claim of identified optimum gains
or stationary position hold. The preserved v88 is the measured baseline.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_heading_hold import PLAN as BASE,RelativeHeadingController

PLAN=dict(BASE,name='two_deck_lower_pitch_integral_v89',ap_ki=.15/.12,
          active_message='QUIET_BALANCE_ACTIVE: 低积分对照版平衡补偿已开始，红点亮起。最多30秒；请只轻扶防倒，原力矩、轮速、温度、倾角和位移停止条件保留。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-quiet',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
