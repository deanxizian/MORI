#!/usr/bin/env python3
"""One far-angle body-rate comparison on the trial44/45 wheel window.

Only the bounded far-angle reference changes400->450deg/s. The near-angle
reference below60deg, gains, force budgets and all hard stops remain. An older
450deg/s comparison on the smaller wheel window regressed; this combination
is untested and is not asserted to succeed. Default inert, finite explicit
launch, no automatic retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_morning_supply import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_window_momentum_v63',
    recovery_rate_max_dps=450.,
    active_message='WINDOW_MOMENTUM_ACTIVE: 第46轮单次起身已启动，最多40秒；仅将起身初段软目标改为450°/秒。向内硬500、向外400、接管后200°/秒，轮速软14.5/硬15.5rad/s、净目标0.35Nm、70°C及其他停止条件保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial46_overturn_and_regressed_closest_pitch37.38deg: retired450deg/s window comparison; use reviewed successor after reset'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-window-momentum',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
