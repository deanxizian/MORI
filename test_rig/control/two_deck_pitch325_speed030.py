#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite outer-speed comparison against the verified P3.25 baseline.

Trial71 reduced the travel envelope but retained slow reciprocal movement.
Keep the complete pitch loop, actuator adapter and guards; change only the
existing zero-speed reference gain0.25to0.30rad/(m/s). This is a modest local
experiment, not a new wheel-rate loop, position integrator or AP default.
The input remains the explicitly documented body-relative encoder proxy.
No automatic start, fallback launch or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_325 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

PLAN=dict(BASE,name='two_deck_pitch325_speed030_v143',
          speed_kp_rad_per_m_s=.30,
          control_phase='two_deck_pitch325_speed030',
          active_message='SPEED030_ACTIVE: 补偿已开始，红点亮、提示音一次，最多30秒。姿态P3.25不变，仅将零速反馈0.25调到0.30；全程不推碰，手只准备接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留；结束两声和红点熄灭后接住。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-pitch325-speed030',
                      controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
