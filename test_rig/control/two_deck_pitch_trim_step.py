#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Second bounded static-trim step after trial47's reduced but residual drift.

Only MORI forward pitch trim changes from +0.1 to +0.2 degrees. All v119
gains, actuator allocation, duration, health checks and motion bounds remain.
This is an experimental setpoint, not a measured COM or IMU recalibration.
No automatic trim adaptation, motion on import, or automatic rearming.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_pitch_trim import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_pitch_trim_step_v120',
            pitch_trim_forward_deg=.2,
            control_phase='two_deck_pitch_trim_step',
            active_message='PITCH_TRIM_STEP_ACTIVE: 补偿已开始，红点亮起，最多30秒。仅将静态俯仰微调从0.1度改为0.2度；全程不推碰，手只防倒。红点灭后接住车身。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-pitch-trim-step',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
