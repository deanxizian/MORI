#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Same v138 controls and guards; extend the finite observation to60 seconds."""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_position_hold import PositionHoldController
from two_deck_trim_position_return import PLAN as BASE

PLAN=dict(BASE,name='two_deck_trim_position_observe_v139',duration_s=60.,
          control_phase='two_deck_trim_position_observe',
          active_message='POSITION_OBSERVE_ACTIVE: 同参数60秒补偿已开始，红点亮、提示音一次；保持手只防倒，全程不推碰，结束两声提示音和红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原异常停止条件保留。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-trim-position-observe',
                      controller=PositionHoldController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
