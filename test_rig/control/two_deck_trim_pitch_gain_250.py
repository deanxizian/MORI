#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded pitchP2.50 comparison after trial56's finite P2.25 observation.

Only physicalP changes2.25to2.50Nm/rad; comparison duration is30s.
Retain0.2degree trim, I/D/filter, outer reference, exact NET allocation and
all output/health/travel guards. Trial55/56 lower speedRMS motivates a small
further step, not a guaranteed improvement or identified hardware model.
No automatic launch, parameter change during motion, or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_upper import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_pitch_gain_250_v129',
            ap_kp=2.50 / BASE['output_scale_nm'],
            control_phase='two_deck_trim_pitch_gain_250',
            active_message='TRIM_PITCH_GAIN_250_ACTIVE: 补偿已开始，红点亮起，最多30秒。仅将姿态P从2.25提高到2.5，其余参数不变；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-pitch-gain-250',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
