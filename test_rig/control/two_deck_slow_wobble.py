#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Single-variable lower-integral comparison on the v101/v98 baseline.

Trial26 has a user-confirmed untouched latter segment with slow reciprocal
motion. AP's Balance Bot tuning guide identifies excess I as one possible
cause, not a diagnosis. Reduce physical Ki0.60to0.15 Nm/(rad*s); preserve
P, D, velocity reference, exact actuator allocation and all stop conditions.
The older v89 also used0.15 but had different velocity/native-damper settings;
its result is not transferred to this candidate. No plant improvement claim.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_velocity_diagnostics import PLAN as BASE,VelocityDiagnosticsController

PLAN=dict(BASE,name='two_deck_lower_integral_current_baseline_v102',
          ap_ki=.15/.12,
          control_phase='two_deck_lower_integral_diagnostics',
          active_message='LOWER_INTEGRAL_ACTIVE: 补偿已开始，红点亮起，最多30秒。只降低姿态积分；其余沿用上一轮，请全程不推碰、手只准备接住。0.12Nm、6rad/s、正负30度、70度及其他停止条件保留。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-slow-wobble',
        controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
