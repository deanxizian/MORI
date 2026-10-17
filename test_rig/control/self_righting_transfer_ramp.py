#!/usr/bin/env python3
"""One slower preparation-to-rise torque transition, no new force budget.

Restore trial45's400deg/s reference after350/450 comparisons regressed.
Only reversal blending duration changes0.08->0.15s; preparation, wheel window,
near-angle law, force budgets and all hard guards remain. A gentler commanded
reversal is not proof of less physical hopping or successful capture.
Default inert; one explicit finite launch, no retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_morning_supply import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_transfer_ramp_v65',
    rise_ramp_s=.15,
    active_message='TRANSFER_RAMP_ACTIVE: 第48轮单次起身已启动，最多40秒；初段目标恢复400°/秒，反转建立时间0.15秒。轮速软14.5/停止15.5rad/s、净目标0.35Nm、70°C及原有停止条件保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial48_overturn_and_ramp_regression: retired0.15s comparison; use reviewed successor after reset'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-transfer-ramp',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
