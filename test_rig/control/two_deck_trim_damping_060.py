#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite D0.060 comparison of the selected P2.75 controller.

Trial59 has residual 6-15 Hz angular-rate/D-term energy. This motivates
changing only physical D0.075 to0.060, not a claim that D caused vibration.
Keep the 10 Hz derivative filter, P/I, trim, speed reference, allocation and
every output/health/travel guard. Use a30s comparison before longer evidence.
No automatic start, gain changes during motion or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_damping_060_v132',
            ap_kd=.060 / BASE['output_scale_nm'],
            control_phase='two_deck_trim_damping_060',
            active_message='TRIM_DAMPING_060_ACTIVE: 补偿已开始，红点亮起，最多30秒。保持P2.75，仅将姿态D从0.075降到0.060；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-damping-060',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
