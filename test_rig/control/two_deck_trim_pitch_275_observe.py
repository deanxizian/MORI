#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Duration-only60s observation of trial58's P2.75 finite controller.

Trial58 reduced matched7-30s encoder span/speedRMS versus57. Preserve its
complete controller and every output/health/travel guard, changing only the
finite observation duration30to60s. Short comparisons do not certify longer
convergence, absence of operator contact, or disturbance recovery.
No automatic launch, background balancing, or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_pitch_275_observe_v131', duration_s=60.,
            control_phase='two_deck_trim_pitch_275_observe',
            active_message='TRIM_PITCH_275_OBSERVE_ACTIVE: 补偿已开始，红点亮起，最多60秒。保持上一轮P2.75及其余全部控制参数；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度、累计2米及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-pitch-275-observe',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
