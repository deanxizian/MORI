#!/usr/bin/env python3
"""One post-night supply/temperature comparison after explicit user resumption.

Retains executed trial44 control settings. Supply is measured, not assumed
full. User unplugged the charger/restored the lying pose; fresh mode0 timing
and sensor checks passed. Old entries remain held. No default hardware I/O,
no automatic retry or fault rearm, one explicit finite launch only.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_headroom_window import PLAN as HELD_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(HELD_PLAN,name='first_layer_morning_supply_v62',
    active_message='MORNING_SUPPLY_ACTIVE: 第45轮单次起身已启动，最多40秒；沿用第44轮参数。轮速软14.5、正常退出14.8、硬停止15.5rad/s，净目标0.35Nm、70°C及原有异常条件保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial45_overturn: retired unchanged-supply comparison; use reviewed successor after physical inspection/reset'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-morning-supply',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
