#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ten-second upright comparison reducing native velocity damping only.

At around3rad/s, old0.025Nm/(rad/s) damping offsets about0.075Nm of a0.12Nm
feedforward request in the same direction. Lowering to0.010 retains more
drive authority under the same FF, predicted net and feedback torque bounds.
These are command predictions, not a measured torque-speed characterization.
"""
from air_trial import main as trial_main
from ground_ardupilot_balance import ArduPilotBalanceController
from ground_hold_trial import HoldTravel
from two_deck_fused_roll import PLAN as PREVIOUS

PLAN = dict(PREVIOUS,name='two_deck_upright_lower_native_damping_v81',
            native_wheel_damping_nm_per_rad_s=.010)
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='Trial03 stopped on fast oscillation and wheel speed; retired for actuator response review.'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-lower-damping',
                      controller=ArduPilotBalanceController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__ == '__main__':raise SystemExit(main())
