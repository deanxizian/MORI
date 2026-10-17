#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Gentle encoder-origin return around the v98 balance controller.

Reuse PositionHoldController, not a new position algorithm. Return velocity
is capped at0.01m/s with positionP0.30/s. The previous v90/v91 position trial
used0.03m/s/0.50/s and older filtering/output/reference settings and worsened
fore-aft motion; it is not adopted. Current reference/output/active guards
stay unchanged. Encoder origin is a proxy, not world/slip-corrected position.
No push during this30s observation, automatic rearm, or continuous driving.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_drive_headroom import PLAN as BASE
from two_deck_position_hold import PositionHoldController

PLAN=dict(BASE,name='two_deck_gentle_encoder_origin_v99',
          allow_position_velocity_target=True,
          position_speed_kp_per_s=.30,position_speed_limit_m_s=.01,
          control_phase='two_deck_gentle_encoder_origin_pid',
          active_message='GENTLE_POSITION_ACTIVE: 补偿已开始，红点亮起，最多30秒。这轮不推碰，记录编码器起点，回中速度目标最多1厘米每秒；其余FF/净命令0.12Nm、轮速6rad/s、正负30度、70度及原停止保护保留。请只防倒，观察前后活动范围。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-gentle-position',
                      controller=PositionHoldController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
