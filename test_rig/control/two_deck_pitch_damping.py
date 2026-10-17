#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One-factor pitch-D comparison against the completed v101/v98 baseline.

Trials26 and28 both show unassisted reciprocal motion. Lowering I did not
reduce the requested travel span, so restore baseline I0.60 and compare
only physical pitch D0.050to0.075 Nm/(rad/s) against trial26. Upstream's
Balance Bot guide identifies D as a damping adjustment, with excessive D
able to cause fast oscillation. This is a bounded experiment, not an
identified plant or a claim of improved balance. Keep the existing10Hz D
filter, velocity reference, actuator allocation and every stop condition.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_velocity_diagnostics import PLAN as BASE,VelocityDiagnosticsController


PLAN=dict(BASE,name='two_deck_pitch_damping_comparison_v103',
          ap_kd=.075/.12,
          control_phase='two_deck_pitch_damping_diagnostics',
          active_message='PITCH_DAMPING_ACTIVE: 补偿已开始，红点亮起，最多30秒。恢复原积分，仅增加姿态阻尼；请全程不推碰、手只准备接住。0.12Nm、6rad/s、正负30度、70度及其他停止条件保留。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-pitch-damping',
        controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
