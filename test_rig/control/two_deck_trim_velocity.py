#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Moderate zero-speed feedback comparison on the v120 trim baseline.

Reject v122 derivativeLPF5Hz as a stationary-travel improvement; restore the
v12010Hz derivative filter and all other v120 parameters. Compare only outer
speedP0.25to0.35rad/(m/s) with the same +0.2degree trim and30s finite window.
Earlier higher-speed-gain tests had different pitch gains and zero trim and
do not prove this new combination. All output, actual-motion and health
guards remain. No automatic motion or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_pitch_trim_step import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_velocity_v123',
            speed_kp_rad_per_m_s=.35,
            control_phase='two_deck_trim_velocity',
            active_message='TRIM_VELOCITY_ACTIVE: 补偿已开始，红点亮起，最多30秒。恢复原10Hz滤波和0.2度微调，仅将零速反馈0.25改为0.35；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-velocity',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
