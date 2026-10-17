#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Duration-only observation of v120 after trial48's smaller travel envelope.

Keep the +0.2 degree experimental trim and every gain, packet allocator and
actual-motion/health bound. Extend only the finite window30to60seconds to
check whether the reduced drift persists. No autonomous start or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_pitch_trim_step import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_observe_v121', duration_s=60.,
            control_phase='two_deck_trim_observe',
            active_message='TRIM_OBSERVE_ACTIVE: 补偿已开始，红点亮起，最多60秒。保留0.2度微调和上一轮全部控制参数；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-observe',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
