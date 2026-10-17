#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Duration-only60s observation of finite trial55's pitchP2.25 controller.

Trial55 reduced matched7-30s encoder speedRMS and travel span versus53.
That short comparison does not establish longer convergence or untouched
standing. Preserve every controller parameter, output/health/travel guard
and stopped-state lifecycle; only the observation duration changes30to60s.
No automatic launch, continuous service or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_upper import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_pitch_gain_observe_v128', duration_s=60.,
            control_phase='two_deck_trim_pitch_gain_observe',
            active_message='TRIM_PITCH_GAIN_OBSERVE_ACTIVE: 补偿已开始，红点亮起，最多60秒。保持上一轮P2.25及其余全部控制参数；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度、累计2米和原异常停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-pitch-gain-observe',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
