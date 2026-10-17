#!/usr/bin/env python3
"""One finite early reversal comparison after trials49/50.

Reduce only reverse preparation target9.5to8rad/s. Keep0.15m planned exit,
0.30m hard net, same rise speed/force/capture/thermal and sensor safeguards.
This is a hardware experiment, not an assumed successful trajectory. Default
inert, no automatic retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_travel_window import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_preroll_early_v68',
    pre_roll_target_rad_s=8.,
    active_message='EARLY_PREROLL_ACTIVE: 第51轮单次起身已启动，最多40秒；仅预滚目标9.5降至8rad/s。起身轮速软15.5、反馈停止16.5rad/s，净目标0.35Nm、70°C和原有行程/传感器/通信保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial51_failed_without_improving_best; retire used entry and restore9.5 reference'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-early-preroll',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
