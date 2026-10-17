#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite derivative-filter comparison against the selected P2.75 baseline.

Only the D-term low-pass changes from 10 to 7.5Hz. The earlier 5Hz test
used P2.0 and was not selected; it does not establish this candidate's
effect. Lower bandwidth can add phase lag. All gains, trim, motor budgets
and fault/travel guards remain unchanged. No automatic start or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN=dict(BASE,name='two_deck_trim_dfilter_75_v136',ap_fltd_hz=7.5,
          control_phase='two_deck_trim_dfilter_75',
          active_message='DFILTER_75_ACTIVE: 补偿已开始，红点亮起，最多30秒。仅将D项滤波从10Hz改为7.5Hz；手只准备接住，不扶住、不推碰。红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及全部原停止条件保留。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-trim-dfilter-75',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
