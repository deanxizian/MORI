#!/usr/bin/env python3
"""Finite recovery comparison using per-wheel host receive times for rates.

Same actuator gains/references and hard stops as v54. Host receive timing fixes
the mixed IMU/encoder interval bug; it is not a servo hardware timestamp or
proof of no slip. No default I/O, no automatic fault retry or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_turn_context import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_torque_rate_recovery_v55_1_feedback_time',
    use_wheel_feedback_timestamps=True,
    active_message='FEEDBACK_TIME_RECOVERY_ACTIVE: 第38轮单次起身开始，最多40秒；编码器轮速改用各轮回包时间，驱动参数不变。净目标0.35Nm、15.5rad/s、起身400°/秒、70°C及其他异常停止条件保留，不自动重试。')
PLAN['motion_hold_reason']='trial38_overturn: retired launch; use reviewed mid-lift successor only'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-feedback-time-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
