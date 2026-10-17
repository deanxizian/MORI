#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite D0.090 comparison against the selected P2.75/D0.075 baseline.

Trial60 lowering D to0.060 increased speed/rate RMS without a clear benefit.
Compare the opposite small step, D0.075 to0.090. Retain P/I, 10 Hz filter,
trim, outer reference, exact output allocation and every health/travel guard.
This is a bounded experiment, not an identified damping or noise model.
No automatic start, gain changes during motion or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_damping_090_v133',
            ap_kd=.090 / BASE['output_scale_nm'],
            control_phase='two_deck_trim_damping_090',
            active_message='TRIM_DAMPING_090_ACTIVE: 补偿已开始，红点亮起，最多30秒。保持P2.75，仅将姿态D由原版0.075提高到0.090；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-damping-090',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
