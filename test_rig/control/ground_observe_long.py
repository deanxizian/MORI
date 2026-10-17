#!/usr/bin/env python3
"""Explicit sixty-second restrained observation; zero hardware I/O by default.

This gives the operator time to read the start message and make one small
fore/aft perturbation. Only duration and presentation differ from the existing
ground profile. All torque, speed, temperature, tilt and cumulative travel
stops remain unchanged. There is no restart after a stop.
"""
from air_trial import main as trial_main
from ground_trial import GROUND_PLAN, WheelTravel, ground_command


LONG_OBSERVE_PLAN=dict(
    GROUND_PLAN,name='restrained_ground_observation_60s_v5',duration_s=60.,
    active_message='RESTRAINED_GROUND_ACTIVE: 最多 60 秒扶护观察开始；只给一个很小的前倾，随后停止主动晃动，始终轻扶防倒并允许轮子小幅滚动。任一停止条件触发即结束，不自动重启。',
)


def main(argv=None):
    return trial_main(argv,plan=LONG_OBSERVE_PLAN,
                      start_flag='--run-restrained-ground-long-observation',
                      controller=ground_command,travel_factory=WheelTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
