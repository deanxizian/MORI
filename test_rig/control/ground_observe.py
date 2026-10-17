#!/usr/bin/env python3
"""Explicitly started ten-second restrained ground observation, zero I/O by default.

The only control-profile difference from ground_trial is the observation
duration. Onsite support and a fresh local start are required for each run.
"""
from air_trial import main as trial_main
from ground_trial import GROUND_PLAN, WheelTravel, ground_command


OBSERVE_PLAN=dict(GROUND_PLAN,name='restrained_ground_observation_10s_v5',duration_s=10.,
                 active_message='RESTRAINED_GROUND_ACTIVE: 10 秒观察开始；轻轻前倾一点，再只扶护防倒，允许车身和轮子小幅活动。')


def main(argv=None):
    return trial_main(argv,plan=OBSERVE_PLAN,start_flag='--run-restrained-ground-observation',
                      controller=ground_command,travel_factory=WheelTravel,description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
