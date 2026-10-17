#!/usr/bin/env python3
"""Opt-in200Hz sensor-driven comparison after disabled timing qualification.

Keep all trial58 control gains, budgets, capture and stable criteria. Only
request200Hz BMI323 ODR with the same ODR/4 selection; physical bandwidth also
changes with ODR. Active loop is data-ready driven, not a hard realtime claim.
Require at least180active cycles/second over the full successful duration;
default profiles remain100Hz/90minimum. Same finite/fault-stop lifecycle.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_capture_velocity_window import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_rate200_v77',imu_odr_hz=200,
    active_message='RATE200_ACTIVE: 第59轮单次起身已启动，最多40秒；控制参数沿用第58轮，仅采样改为200Hz/ODR四分之一带宽。净目标0.35Nm、轮速16.5rad/s、70°C及原有全部保护和30秒稳定标准保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial59_failed_without_capture;200Hz timing observed, used launch retired'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-rate200',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
