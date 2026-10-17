#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Duration-only60s observation of trial61's P2.75/D0.090 controller.

The30s comparison reduced pitch RMS slightly but did not reduce fast rate
variation. Preserve its full controller and guards for a longer comparison;
this is not a claim of improved vibration, stationary hold or recovery.
No automatic start, adaptation or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_damping_090 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_damping_090_observe_v134', duration_s=60.,
            control_phase='two_deck_trim_damping_090_observe',
            active_message='TRIM_DAMPING_090_OBSERVE_ACTIVE: 补偿已开始，红点亮起，最多60秒。保持上一轮P2.75和D0.090及其余全部参数；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度、累计2米及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-damping-090-observe',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
