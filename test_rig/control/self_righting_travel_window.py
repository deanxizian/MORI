#!/usr/bin/env python3
"""One bounded travel-reserve comparison following recorded trial49.

Move only the planned early exit from0.10m to0.15m encoder-equivalent net
travel. Hard net0.30m and cumulative1.00m remain. Speed, force, body, capture,
thermal, sensor and communication checks unchanged. No assumption of traction
or actual ground travel. Default inert, single explicit launch, no retry.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_speed_window import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_travel_window_v67',
    abort_net_reserve_trigger_m=.15,
    active_message='TRAVEL_WINDOW_ACTIVE: 第50轮单次起身已启动，最多40秒；提前退出转量0.15m，硬停止转量0.30m及累计1m保留。轮速软15.5、反馈停止16.5rad/s，净目标0.35Nm、70°C和原有保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial50_outward_return_before_travel_window; retired launch after physical FAIL'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-travel-window',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
