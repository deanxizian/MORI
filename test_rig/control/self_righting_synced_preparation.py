#!/usr/bin/env python3
"""One synchronized preparation-gate comparison at the original9.5rad/s.

Relative to trial50 only require BOTH wheels to reach preparation target;
trial51's8rad/s adjustment is withdrawn. Time/travel and independent13rad/s
preparation stop remain. All rise/force/capture/thermal/communication guards
unchanged. Default inert, finite explicit launch, no automatic retry/rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_travel_window import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_synced_preparation_v69',
    pre_roll_target_both_wheels=True,
    active_message='SYNCED_PREPARATION_ACTIVE: 第52轮单次起身已启动，最多40秒；恢复预滚9.5rad/s，等待两轮都达到目标再切换，预滚独立13rad/s及0.4s上限保留。起身轮速软15.5、反馈停止16.5rad/s，净目标0.35Nm、70°C和原有保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial52_physical_FAIL; used entry retired before native preparation successor'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-synced-preparation',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
