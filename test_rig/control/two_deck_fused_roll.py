#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Same upright baseline with the existing gyro/gravity roll estimator.

Trial01 rejected an11.14deg instantaneous accelerometer roll while pitch was
-3.89deg and inferred roll rate-1.22deg/s. Fused roll avoids interpreting a
single translational acceleration as an instantaneous physical roll. This
does not remove roll protection, increase torque, or establish balance.
"""
from air_trial import main as trial_main
from ground_ardupilot_balance import ArduPilotBalanceController
from ground_hold_trial import HoldTravel
from two_deck_balance import PLAN as BASELINE

PLAN = dict(BASELINE, name='two_deck_upright_fused_roll_v80', fuse_roll=True)
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='Trial02 reached pitch stop; retired for reviewed lower-native-damping comparison under the same net budget.'


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-fused-roll',
                      controller=ArduPilotBalanceController(),
                      travel_factory=HoldTravel, description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
