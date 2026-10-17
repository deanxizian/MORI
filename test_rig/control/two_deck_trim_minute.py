#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite60s check of v120 after later gain/filter comparisons were rejected.

v121 held a small encoder envelope until the1m cumulative reciprocal-path
budget stopped it at47.66s. Retain the v120 controller exactly and provide
2m cumulative path for one60s observation. Per-wheel net offset0.30m,
differential offset0.03m and every output/speed/attitude/health guard remain.
Cumulative encoder rotation is not net floor displacement. No unlimited
operation, autonomous start or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_observe import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_minute_v125', rolling_path_limit_m=2.,
            control_phase='two_deck_trim_minute',
            active_message='TRIM_MINUTE_ACTIVE: 补偿已开始，红点亮起，最多60秒。保留0.2度微调和零速反馈0.25；累计往返窗口2米，离起点净转量仍30厘米。全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原异常停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-minute',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
