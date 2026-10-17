#!/usr/bin/env python3
"""Restrained comparison with earlier proportional attitude correction.

Trial 11 still showed stationary wheels near two degrees of target error,
with roughly 0.05 Nm commanded. Increase only body proportional gain from
1.5 to 3 Nm/rad. Keep the 0.12 Nm command envelope, both damping terms and
every stop threshold. Default invocation never opens hardware.
"""
from air_trial import main as trial_main
from ground_trial import WheelTravel, ground_command
from ground_recovery_trial import RECOVERY_PLAN


EARLY_PLAN=dict(
    RECOVERY_PLAN,name='restrained_ground_earlier_p3_v7',kp_nm_per_rad=3.,
    active_message='RESTRAINED_GROUND_ACTIVE: 提前纠偏版开始，最多 60 秒；只给一个很小的前倾，随后停止主动晃动，始终轻扶防倒并允许轮子小幅滚动。0.12 Nm 命令上限及原停止条件保留。',
)


def main(argv=None):
    return trial_main(argv,plan=EARLY_PLAN,
                      start_flag='--run-restrained-ground-early-response',
                      controller=ground_command,travel_factory=WheelTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
