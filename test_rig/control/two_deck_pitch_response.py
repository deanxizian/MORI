#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ten-second pitch-P comparison against the selected v101 baseline.

Reject native-execution variants113–115 as demonstrated stationary-hold
improvements: trial43 completed30s but had greater encoder drift and pitch
motion than26. Restore v101 actuator/reference/I/D/mixer, compare physical
pitchP1.5to2.0 Nm/rad only, and shorten the initial window to10s. The official
AP Balance Bot guide describes pitch-P tuning; this value is a local bounded
experiment, not an upstream gain, friction identification or stability proof.
All original output, actual-motion, health and stop conditions remain.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_velocity_diagnostics import PLAN as BASE, VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_pitch_response_v116', duration_s=10.,
            ap_kp=2.0/.12, control_phase='two_deck_pitch_response',
            active_message='PITCH_RESPONSE_ACTIVE: 补偿已开始，红点亮起，最多10秒。恢复旧版执行方式，仅提高姿态比例增益；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-pitch-response',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
