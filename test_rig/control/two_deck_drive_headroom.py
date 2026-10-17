#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""30s native-damper headroom comparison against v97.

Only native wheel damping changes0.010to0.005Nm/(rad/s). The exact allocator
already compensates it within FF/NET limits; at high speed this leaves more
same-direction NET authority below the unchanged0.12Nm FF cap. This is a
prediction, not a measured shaft-torque clamp. All control/reference and
active health/stop settings remain unchanged. No automatic retry or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_braking_reference import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController

PLAN=dict(BASE,name='two_deck_native_damper_headroom_v98',
          native_wheel_damping_nm_per_rad_s=.005,
          control_phase='two_deck_native_damper_headroom_pid',
          active_message='DRIVE_HEADROOM_ACTIVE: 补偿已开始，红点亮起，最多30秒。仅降低原生轮速阻尼以保留高速纠偏余量；FF/净命令0.12Nm、轮速6rad/s、车身正负30度、70度及其他停止保护不变。请先只防倒，等提示后只做一次很轻的短促推碰。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-drive-headroom',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
