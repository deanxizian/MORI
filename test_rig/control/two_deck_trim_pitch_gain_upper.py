#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite upper pitch-P comparison around selected v120/v125 settings.

Trial54 at physicalP1.75 increased the matched7-30s encoder travel envelope
to5.22cm versus2.80cm atP2.0 in53. CompareP2.25 for30s, retaining v125's
trim, I/D, outer reference, exact actuator allocation and all motion guards.
This bracket is experimental: different initial/thermal conditions do not
identify a causal plant model. No automatic launch or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_minute import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_pitch_gain_upper_v127', duration_s=30.,
            ap_kp=2.25 / BASE['output_scale_nm'],
            control_phase='two_deck_trim_pitch_gain_upper',
            active_message='TRIM_PITCH_GAIN_UPPER_ACTIVE: 补偿已开始，红点亮起，最多30秒。保留0.2度微调，仅将姿态P从基准2.0提高到2.25；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原转量和异常停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-pitch-gain-upper',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
