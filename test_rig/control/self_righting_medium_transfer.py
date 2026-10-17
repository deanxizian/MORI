#!/usr/bin/env python3
"""Intermediate0.06s transfer, restoring the trial50 torque profile.

The0.04s experiment hit3.176g and is retired. Compare0.06against original0.08;
all existing acceleration/force/speed/capture/temperature/travel guards remain.
Default inert, one finite explicit launch, no retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_travel_window import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_medium_transfer_v73',rise_ramp_s=.06,
    active_message='MEDIUM_TRANSFER_ACTIVE: 第56轮单次起身已启动，最多40秒；原力矩预滚9.5rad/s，反转过渡0.06秒。加速度保护不变，轮速软15.5、反馈停止16.5rad/s，净目标0.35Nm、70°C及原有行程/传感器/通信保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial56_outward_return_no_capture; retire used entry before bounded governor comparison'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-medium-transfer',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
