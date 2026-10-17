#!/usr/bin/env python3
"""Same fixed-reference controller with a bounded larger observation area.

Trial 15 stopped at 4.026 cm right-wheel net rolling equivalent, with body
pitch 2.414 degrees. Change only the net offset budget to 10 cm; retain all
gains, 30-second duration, cumulative budget, speed and other stop conditions.
Encoder-derived distances are not measured floor travel or a physical fence.
"""
from air_trial import main as trial_main
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from ground_reduced_damping import REDUCED_DAMPING_PLAN


TRAVEL_WINDOW_PLAN=dict(
    REDUCED_DAMPING_PLAN,name='restrained_ground_fixed_reference_net10cm_v11',
    net_rolling_limit_m=.10,
    active_message='RESTRAINED_GROUND_ACTIVE: 同参数观察开始，最多 30 秒；每轮净转量折算上限 10 cm，累计仍为 40 cm。请轻扶防倒，不要持续主动晃动；原速度、力矩、温度和姿态停止条件仍生效。',
)


def main(argv=None):
    return trial_main(argv,plan=TRAVEL_WINDOW_PLAN,
                      start_flag='--run-restrained-ground-travel-window',
                      controller=ground_command,travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
