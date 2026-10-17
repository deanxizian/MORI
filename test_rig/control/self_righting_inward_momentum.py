#!/usr/bin/env python3
"""One finite inward-momentum comparison; operator onsite, no retry/rearm.

Reverts v56's ineffective middle-angle feedforward. Only inward body speed
allowance is higher: reference400 and RISING hard500deg/s; outward hard400 and
balance hard200 remain. Actuator net torque0.35Nm/wheel speed15.5rad/s/70C
limits are unchanged. Not a self-righting guarantee or validated energy model.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_feedback_time import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_torque_rate_recovery_v57_inward_momentum',
    allow_inward_rate_extension=True,
    recovery_rate_max_dps=400.,rise_pitch_rate_limit_dps=500.,rise_outward_pitch_rate_limit_dps=400.,
    active_message='INWARD_MOMENTUM_RECOVERY_ACTIVE: 第40轮单次起身开始，最多40秒；向直立方向软目标400/停止500°每秒，倒回方向停止400，直立后200。净目标0.35Nm、15.5rad/s、70°C及其他异常停止条件保留，不自动重试。')
PLAN['motion_hold_reason']='trial40_overturn: retired400deg/s launch; use reviewed successor'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-inward-momentum-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)

if __name__=='__main__':raise SystemExit(main())
