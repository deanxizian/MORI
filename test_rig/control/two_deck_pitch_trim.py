#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small fixed-pitch-trim comparison for sustained rearward drift in trial46.

Official AP Balance Bot tuning uses0.1degree pitch-trim steps. AP positive
pitch is backwards; MORI positive pitch is forwards. Thus the documented
backward-drift trim direction maps to +0.1degree here. This is an experiment,
not a measured COM angle or a change to IMU calibration. Keep v118 gains,
backend,30s duration and all motion/health/stop bounds. No automatic rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_damped_observe import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_pitch_trim_v119', pitch_trim_forward_deg=.1,
            control_phase='two_deck_pitch_trim',
            active_message='PITCH_TRIM_ACTIVE: 补偿已开始，红点亮起，最多30秒。仅比较0.1度静态俯仰微调；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-pitch-trim',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
