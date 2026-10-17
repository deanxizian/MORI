#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Derivative-filter comparison with v120's experimental +0.2degree trim.

Trial49 shows a slow reciprocal component and7-8Hz components in body rate
and derivative torque. Their cause is not identified. Compare only the
ported PID derivative LPF10to5Hz in a30s window; retain all gains, allocation,
trim and motion/health bounds. This may also reduce phase margin; it is an
experiment, not established noise rejection or a balance qualification.
No automatic motion, adaptation or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_pitch_trim_step import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_dfilter_v122', ap_fltd_hz=5.,
            control_phase='two_deck_trim_dfilter',
            active_message='TRIM_DFILTER_ACTIVE: 补偿已开始，红点亮起，最多30秒。保留0.2度平衡微调，仅将姿态D项滤波从10Hz改为5Hz；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-dfilter',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
