#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite, no-push velocity-P comparison against v98.

Change only speed-to-pitch P from0.25to0.40rad/(m/s). Reuse the existing
50ms filter,3deg reference bound,6deg/s reference slew, pitch PID, heading
mix and exact NET allocator. This is an experimental local gain, not an
upstream default or a measured closed-loop improvement. The hand-fixed
tail of trial23 cannot establish a balance trim. No new integral or common
position loop, automatic start, retry or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_drive_headroom import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController


PLAN=dict(BASE,name='two_deck_velocity_p_comparison_v100',
          speed_kp_rad_per_m_s=.40,
          control_phase='two_deck_velocity_p_comparison_pid',
          active_message='VELOCITY_P_ACTIVE: 补偿已开始，红点亮起，最多30秒。这轮不推碰，手只防倒，让车身自行纠偏。速度反馈P由0.25改为0.40；每轮FF/净命令0.12Nm、轮速6rad/s、车身正负30度、70度及其余停止条件保留。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-speed-damping',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
