#!/usr/bin/env python3
"""Fixed-reference restrained trial with the previously tested body-rate D.

Trial 14 had rapid command reversals before a 0.131 Nm estimated-torque stop.
Return only the attitude rate gain from 0.08 to 0.05 Nm/(rad/s), as in trial 12.
Keep fixed calibrated zero and every v9 command, timing and stop boundary.
This is a comparison candidate, not a proven cure or validated balance gains.
"""
from air_trial import main as trial_main
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from ground_fixed_reference import FIXED_PLAN


REDUCED_DAMPING_PLAN=dict(
    FIXED_PLAN,name='restrained_ground_fixed_reference_reduced_rate_damping_v10',
    kd_nm_per_rad_s=.05,
    active_message='RESTRAINED_GROUND_ACTIVE: 固定零点、降低姿态 D 的对照开始，最多 30 秒；请轻扶防倒，给很小的扰动后停止主动晃动。原力矩、速度、温度和转量停止条件仍生效。',
)


def main(argv=None):
    return trial_main(argv,plan=REDUCED_DAMPING_PLAN,
                      start_flag='--run-restrained-ground-reduced-damping',
                      controller=ground_command,travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
