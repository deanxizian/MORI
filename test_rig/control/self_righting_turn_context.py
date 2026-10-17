#!/usr/bin/env python3
"""Finite recovery with brief gyro-only continuation through a turning point.

Only RISING opts into <=20 ms recent fast-rotation context for the existing
short low-specific-force event. All other estimator and actuator guards remain.
Recent context is not evidence against hopping/freefall. No retry or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_torque_recovery_low_damping import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_torque_rate_recovery_v54_turn_context',
    rotating_low_g_history_s=.02,
    active_message='TURN_CONTEXT_RECOVERY_ACTIVE: 第37轮单次起身开始，最多40秒；仅修正RISING短时动态判据，力矩和速度参数不变。净目标0.35Nm、15.5rad/s、起身400°/秒、70°C及其他异常停止条件保留，不自动重试。')
PLAN['motion_hold_reason']='trial37_overturn: retired launch; use time-boundary successor only'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-turn-context-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
