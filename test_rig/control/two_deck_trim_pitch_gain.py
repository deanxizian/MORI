#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite pitch-P comparison after the v120/v125 drift-trim observation.

Trial53 completed60s but retained reciprocal encoder travel about3cm.
Reduce physical pitchP2.0to1.75Nm/rad while retaining its0.2degree trim,
I/D, speed/heading controllers, actuator allocation and every guard. This
is a30s comparison, not an identified plant or demonstrated improvement.
The prior lower-P runs had different trim/controller configurations.
No automatic launch, parameter change during motion or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_minute import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_pitch_gain_v126', duration_s=30.,
            ap_kp=1.75 / BASE['output_scale_nm'],
            control_phase='two_deck_trim_pitch_gain',
            active_message='TRIM_PITCH_GAIN_ACTIVE: 补偿已开始，红点亮起，最多30秒。保留0.2度微调，仅将姿态P从2.0降到1.75；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原转量和异常停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-pitch-gain',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
