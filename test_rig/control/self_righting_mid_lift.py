#!/usr/bin/env python3
"""Finite middle-angle feedforward comparison on the corrected time base.

Same 300 deg/s body reference, torque caps, wheel governor and hard stops.
The added middle-angle term fades before capture and is absent at the initial
90 deg kick and near upright. No default I/O, retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_feedback_time import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_torque_rate_recovery_v56_mid_lift',
    recovery_mid_gravity_ff_nm=.35,recovery_mid_inner_deg=15.,
    recovery_mid_full_near_deg=25.,recovery_mid_full_far_deg=65.,recovery_mid_outer_deg=74.,
    active_message='MID_LIFT_RECOVERY_ACTIVE: 第39轮单次起身开始，最多40秒；只增加中段驱动保持，初始及近直立反馈不变。净目标最多0.35Nm、15.5rad/s、起身400°/秒、70°C及其他异常停止条件保留，不自动重试。')
PLAN['motion_hold_reason']='trial39_overturn_and_no_improvement: retired launch'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-mid-lift-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
