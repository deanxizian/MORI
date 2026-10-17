#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""30s bounded braking-reference authority study against v96.

Keep the existing velocity P/filter and pitchPID/output; enlarge only the
speed-generated target pitch from1to3deg and its slew2to6deg/s (same0.5s
zero-to-full-target time). Actual body pitch still stops at30deg. No higher
torque command, wheel-speed ceiling, position loop, or automatic rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_push_observe import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController

PLAN=dict(BASE,name='two_deck_braking_pitch_authority_v97',
          allow_wide_speed_pitch_reference=True,
          speed_pitch_reference_limit_deg=3.,speed_pitch_reference_slew_dps=6.,
          control_phase='two_deck_braking_pitch_authority_pid',
          active_message='BRAKING_REFERENCE_ACTIVE: 补偿已开始，红点亮起，最多30秒。速度制动目标可调正负3度、6度每秒；实际车身退出线正负30度，FF/净命令0.12Nm、轮速6rad/s、70度及其他保护保留。请先只防倒，等待轻推提示。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-braking-reference',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
