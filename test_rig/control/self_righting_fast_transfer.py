#!/usr/bin/env python3
"""Compare a shorter torque reversal, restoring the trial50 torque path.

The native preparation experiments did not improve the best rise and are
withdrawn. Relative to trial50 only shorten rise transfer0.08to0.04s. All
preparation, speed/force, capture, time/travel, thermal and fault checks remain.
Default inert, one finite explicit launch, no automatic retry or rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_travel_window import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_fast_transfer_v72',rise_ramp_s=.04,
    active_message='FAST_TRANSFER_ACTIVE: 第55轮单次起身已启动，最多40秒；恢复原力矩预滚9.5rad/s，仅反转过渡0.08缩短至0.04秒。轮速软15.5、反馈停止16.5rad/s，净目标0.35Nm、70°C及原有行程/传感器/通信保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial55_3.176g_acceleration_fault; used0.04s profile retired, no acceleration guard relaxation'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-fast-transfer',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
