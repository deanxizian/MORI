#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite P3.25 comparison after trial69's modest P3.00 improvement.

Only the physical pitchP changes3.00to3.25. Retain I/D, zero-speed reference,
exact actuator allocation and all guard thresholds. A single smaller travel
window does not establish causality or stationary operation. No automatic
start, fallback launch, or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_300 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

PLAN=dict(BASE,name='two_deck_trim_pitch_gain_325_v141',
          ap_kp=3.25/BASE['output_scale_nm'],
          control_phase='two_deck_trim_pitch_gain_325',
          active_message='PITCH_325_ACTIVE: 补偿已开始，红点亮、提示音一次，最多30秒。仅将姿态P从3.00调整为3.25；全程不推碰，手只准备接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留；结束两声和红点熄灭后接住。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-trim-pitch-gain-325',
                      controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
