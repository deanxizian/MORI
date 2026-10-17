#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded P2.75 comparison following trial57's smaller encoder envelope.

Only physical pitchP changes2.50to2.75Nm/rad. Duration30s, trim, I/D,
reference filters, exact NET allocation and all motion/health guards remain.
Trial57's smaller envelope is descriptive evidence, not a causal model or
permission to alter torque/thermal limits. No automatic launch or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_trim_pitch_gain_250 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


PLAN = dict(BASE, name='two_deck_trim_pitch_gain_275_v130',
            ap_kp=2.75 / BASE['output_scale_nm'],
            control_phase='two_deck_trim_pitch_gain_275',
            active_message='TRIM_PITCH_GAIN_275_ACTIVE: 补偿已开始，红点亮起，最多30秒。仅将姿态P从2.5提高到2.75，其余参数不变；全程不推碰，手只防倒，红点灭后接住。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件保留。')


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-trim-pitch-gain-275',
                      controller=VelocityDiagnosticsController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
