#!/usr/bin/env python3
"""One finite450deg/s inward-reference comparison; no default I/O or rearm.

Same500deg/s inward,400outward,200balance stops. Torque, wheel speed, thermal,
travel and sensor guards are unchanged. Software checks do not prove self-rise.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_inward_momentum import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_torque_rate_recovery_v58_inward450',
    recovery_rate_max_dps=450.,
    active_message='INWARD450_RECOVERY_ACTIVE: 第41轮单次起身开始，最多40秒；向直立方向软目标450/停止500°每秒，倒回400，直立后200。净目标0.35Nm、15.5rad/s、70°C及其他异常停止条件保留，不自动重试。')
PLAN['motion_hold_reason']='trial41_inward450_regressed: retired launch'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-higher-inward-momentum',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
