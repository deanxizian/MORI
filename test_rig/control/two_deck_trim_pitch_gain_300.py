#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite P3.00 comparison against selected P2.75, with original zero-speed loop.

The v138/v139 position experiment produced one near-static tail but did not
reproduce it in the next mixed push trial. It is not the selected baseline.
Return to v130 and change only pitchP by the same0.25 step previously tested;
all output, timing, thermal, travel and posture guards remain unchanged.
No automatic enable or fault rearm; no claim of zero wheel motion.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

PLAN=dict(BASE,name='two_deck_trim_pitch_gain_300_v140',
          ap_kp=3.00/BASE['output_scale_nm'],
          control_phase='two_deck_trim_pitch_gain_300',
          active_message='PITCH_300_ACTIVE: 补偿已开始，红点亮、提示音一次，最多30秒。回到原零速反馈版，仅将姿态P从2.75调整为3.00；这轮全程不要推碰，手只准备接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留；结束两声和红点熄灭后接住。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-trim-pitch-gain-300',
                      controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
