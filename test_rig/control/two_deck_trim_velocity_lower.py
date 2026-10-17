#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lower zero-speed feedback comparison on the unchanged v120 trim baseline.

Trial51 speedP0.35 did not improve the full matched travel window. Compare
speedP0.15 against the original0.25, retaining +0.2degree trim, all pitchPID
gains,10Hz Dfilter, packet allocation and30s/all guards. This brackets the
outer gain experimentally; it is not proof of a physical oscillation cause.
No automatic motion, adaptation or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_pitch_trim_step import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_velocity_lower_v124',
            speed_kp_rad_per_m_s=.15,
            control_phase='two_deck_trim_velocity_lower',
            active_message='TRIM_VELOCITY_LOWER_ACTIVE: 补偿已开始，红点亮起，最多30秒。保留10Hz滤波和0.2度微调，仅将零速反馈从原0.25降到0.15；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-velocity-lower',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
