#!/usr/bin/env python3
"""Finite torque-interface comparison of the bounded body-rate recovery.

Keeps the v51.1 body reference and all hard motion/thermal limits. Restores the
previous feedforward/native-damping adapter because trial34 delivered a weaker
lift with the native velocity adapter. Not a proven plant or self-righting
controller. Explicit run only; no automatic retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_rate_recovery import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,
    name='first_layer_torque_rate_recovery_v52',
    native_velocity_control=False,
    active_message='TORQUE_RATE_RECOVERY_ACTIVE: 第35轮单次起身开始，最多40秒；恢复力矩接口，姿态反馈和停止条件不变。预测净目标最多0.35Nm、轮速15.5rad/s、起身机身400°/秒、70°C及异常停止；不自动重试。')
PLAN['motion_hold_reason']='trial35_acceleration_fault: retired launch; use reviewed successor only'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-torque-rate-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
