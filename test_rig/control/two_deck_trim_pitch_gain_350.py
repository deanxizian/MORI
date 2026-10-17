#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite P3.50 comparison after trial71's repeatable P3.25 improvement.

Return to selected v141 zero-speedP0.25; v143 speedP0.30 is not selected.
Only pitchP3.25to3.50 changes. Check both slow travel and fast corrections;
all actuator, timing, posture, thermal and travel guards remain unchanged.
No automatic start, fallback launch or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_325 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

PLAN=dict(BASE,name='two_deck_trim_pitch_gain_350_v144',
          ap_kp=3.50/BASE['output_scale_nm'],
          control_phase='two_deck_trim_pitch_gain_350',
          active_message='PITCH_350_ACTIVE: 补偿已开始，红点亮、提示音一次，最多30秒。恢复零速反馈0.25，仅将姿态P从3.25调整为3.50；全程不推碰，手只准备接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留；结束两声和红点熄灭后接住。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-trim-pitch-gain-350',
                      controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
