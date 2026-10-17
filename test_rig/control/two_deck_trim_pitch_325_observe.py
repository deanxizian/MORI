#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Same v141 P3.25 controls; finite60s repeatability comparison only."""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_325 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

PLAN=dict(BASE,name='two_deck_trim_pitch_325_observe_v142',duration_s=60.,
          control_phase='two_deck_trim_pitch_325_observe',
          active_message='PITCH_325_OBSERVE_ACTIVE: 同一组P3.25参数的60秒补偿已开始，红点亮、提示音一次；这轮全程不推碰，手只准备接住。每轮0.12Nm、6rad/s、正负30度、70度及原异常停止条件保留。结束两声和红点灭后接住。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-trim-pitch-325-observe',
                      controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
