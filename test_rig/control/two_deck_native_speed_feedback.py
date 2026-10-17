#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One-factor ground comparison of zero-speed feedback after trial41.

Trial41 completed ten seconds, with less simultaneous near-zero wheel dwell
but greater rearward encoder displacement than baseline26. Native execution
is still experimental, not adopted as improved stationary balance. Compare
only velocity-reference P0.25 to0.40 while retaining v113 pitch PID, native
Kd0.40, integer NET allocation, reference bounds and all actual-motion guards.
This follows the existing AP-derived speed-to-pitch cascade; this local gain
is not an ArduPilot default, identified plant parameter or stability proof.
No I/O by default, automatic launch, self-righting or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_native_execution import PLAN as BASE, NativeExecutionController


PLAN = dict(BASE, name='two_deck_native_speed_feedback_v114',
            speed_kp_rad_per_m_s=.40,
            control_phase='two_deck_native_speed_feedback',
            active_message='NATIVE_SPEED_FEEDBACK_ACTIVE: 补偿已开始，红点亮起，最多10秒。仅增加零速反馈，保持舵机内部执行方式；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN,
                      start_flag='--run-two-deck-native-speed-feedback',
                      controller=NativeExecutionController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
