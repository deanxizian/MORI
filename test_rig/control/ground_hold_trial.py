#!/usr/bin/env python3
"""Thirty-second restrained settling observation; explicit local start only.

After trial 12's operator-confirmed self-correction, increase body rate damping
from 0.05 to 0.08 Nm/(rad/s). Allow up to 0.40 m of cumulative rotor-derived
rolling while stopping at 0.04 m net offset per wheel. These are encoder-derived
equivalents, not measured floor travel or a certified workspace boundary.
"""
from air_trial import main as trial_main
from attitude import Fault
from ground_trial import WheelTravel, ground_command
from ground_early_response import EARLY_PLAN


HOLD_PLAN=dict(
    EARLY_PLAN,name='restrained_ground_damped_hold_v8',duration_s=30.,
    kd_nm_per_rad_s=.08,rolling_path_limit_m=.40,net_rolling_limit_m=.04,
    active_message='RESTRAINED_GROUND_ACTIVE: 最多 30 秒扶护观察开始；只给一个很小的前倾后停止主动晃动，始终防倒。轮子累计转量折算 40 cm、离起点净转量折算 4 cm 或其他保护触发即停止。',
)


class HoldTravel(WheelTravel):
    def __init__(self,rows,signs,plan=HOLD_PLAN):
        super().__init__(rows,signs,plan)

    def update(self,mid,row):
        super().update(mid,row)
        if abs(self.offset[mid])>=self.plan['net_rolling_limit_m']:
            raise Fault('wheel_net_travel_stop')


def main(argv=None):
    return trial_main(argv,plan=HOLD_PLAN,
                      start_flag='--run-restrained-ground-hold',
                      controller=ground_command,travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
