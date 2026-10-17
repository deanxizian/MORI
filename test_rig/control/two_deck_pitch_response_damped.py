#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Damping comparison after the trial44 pitch-P response experiment.

Trial44 reduced pitch RMS but increased gyro-rate RMS and did not reduce
encoder travel. Keep physical P2.0, compare only D0.050to0.075Nm/(rad/s)
within the existing checked AP-derived PID,10Hz D filter and original v101
actuator/reference layers. This hypothesis is not a demonstrated fix or
an identified plant. Original ten-second window and all guards remain.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_pitch_response import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_pitch_response_damped_v117',
            ap_kd=.075/.12, control_phase='two_deck_pitch_response_damped',
            active_message='DAMPED_PITCH_RESPONSE_ACTIVE: 补偿已开始，红点亮起，最多10秒。保持姿态比例增益，仅增加阻尼；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN,
                      start_flag='--run-two-deck-pitch-response-damped',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
