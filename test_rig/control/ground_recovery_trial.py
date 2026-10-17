#!/usr/bin/env python3
"""Explicit restrained recovery trial with a 0.12 Nm feedforward cap.

Experimental comparison after trial 10 hit the 0.08 Nm cap while pitch kept
increasing. Body gains and native damping remain unchanged. Speed, temperature,
estimated-torque, attitude and travel stops are inherited unchanged. This is
not a validated balance profile and does no hardware I/O by default.
"""
from air_trial import main as trial_main
from ground_trial import WheelTravel, ground_command
from ground_observe_long import LONG_OBSERVE_PLAN


RECOVERY_PLAN=dict(
    LONG_OBSERVE_PLAN,name='restrained_ground_recovery_ff012_v6',
    feedforward_torque_limit_nm=.12,predicted_net_torque_limit_nm=.12,
    active_message='RESTRAINED_GROUND_ACTIVE: 0.12 Nm 上限对照开始，最多 60 秒；只给一个很小的前倾，随后停止主动晃动，始终轻扶防倒并允许轮子小幅滚动。到时或异常停止，不自动重启。',
)


def main(argv=None):
    return trial_main(argv,plan=RECOVERY_PLAN,
                      start_flag='--run-restrained-ground-recovery',
                      controller=ground_command,travel_factory=WheelTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
