#!/usr/bin/env python3
"""One lower far-angle reference comparison after the450deg/s regression.

Executed trial45 used400deg/s and reached30.2deg; trial46 used450deg/s and
reached37.4deg. Try350deg/s on the same wheel window, restoring all other
trial45 settings. Near-angle law below52.5deg is unchanged. This target is
not a new hard speed ceiling. No guarantee of success or identified model.
Default inert; one explicit finite run, no retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_morning_supply import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_rate350_v64',
    recovery_rate_max_dps=350.,
    active_message='RATE350_ACTIVE: 第47轮单次起身已启动，最多40秒；起身初段软目标350°/秒。向内硬500、向外400、接管后200°/秒，轮速软14.5/停止15.5rad/s、净目标0.35Nm、70°C及其他异常条件保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial47_overturn_and_no_capture: retired350deg/s comparison; use reviewed successor after physical reset'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-rate350',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
