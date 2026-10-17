#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Thirty-second observation of the unchanged trial42 controller.

The preceding ten-second comparison reduced rearward encoder displacement,
but did not establish stationary holding or longer-term convergence. Only
the finite observation duration changes. No new controller, gain, reference,
actuator authority, physical-motion bound or automatic rearm is introduced.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_native_execution import NativeExecutionController
from two_deck_native_speed_feedback import PLAN as BASE


PLAN = dict(BASE, name='two_deck_native_observe_v115', duration_s=30.,
            control_phase='two_deck_native_observe',
            active_message='NATIVE_OBSERVE_ACTIVE: 补偿已开始，红点亮起，最多30秒。保持上一轮全部控制参数；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-native-observe',
                      controller=NativeExecutionController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
