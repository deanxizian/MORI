#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite encoder-origin return on the selected P2.75/10Hz pitch baseline.

Reuse the existing PositionHoldController: positionP0.30/s and1cm/s target
cap, without a new integrator or native position stiffness. The older v99
position trial did not improve the then-current P1.5 controller; this is an
explicit new comparison on v130, not adoption or proof of that old result.
Keep all selected pitch/velocity/heading gains, output allocation and guards.
Relative encoder origin is not a measured floor location or zero-motion proof.
No automatic enable, self-righting, or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_position_hold import PositionHoldController


PLAN=dict(BASE,name='two_deck_trim_position_return_v138',
          allow_position_velocity_target=True,
          position_speed_kp_per_s=.30,position_speed_limit_m_s=.01,
          control_phase='two_deck_trim_position_return',
          active_message='POSITION_RETURN_ACTIVE: 补偿已开始，红点亮、提示音一次，最多30秒。沿用P2.75和10Hz基线，增加已有的编码器回中控制，回中速度目标最多1厘米每秒；全程不推碰，手只防倒，红点灭及两次提示音后接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-trim-position-return',
                      controller=PositionHoldController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
