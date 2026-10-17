#!/usr/bin/env python3
"""One stronger soft-envelope gain comparison at the verified200Hz cadence.

Change only gain0.25to0.35. Same15.5soft/16.5stop and downstream0.35Nm predicted
net budget, with stronger braking above target as well as drive below it.
Same capture/stable criteria and finite/fault-stop lifecycle; no physical
rise predicted or hardware torque clamp inferred.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_rate200 import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_governor_stronger_v78',rise_speed_gain_nm_per_rad_s=.35,
    active_message='STRONGER_GOVERNOR_ACTIVE: 第60轮单次起身已启动，最多40秒；200Hz，仅速度包络增益0.25改为0.35。15.5rad/s软目标、16.5rad/s停止线、0.35Nm净目标预算和70°C及原有全部保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='User deferred self-righting and added second deck; first-layer v78 was never run and is retired. Use reviewed upright-only entry.'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-stronger-governor',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
