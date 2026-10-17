#!/usr/bin/env python3
"""One explicitly opted-in speed-window experiment, same force budget.

Restore executed trial45's400deg/s reference and0.08s reversal. Soft wheel
target15.5, normal exit15.8, abort target16.0, filtered-feedback hard stop16.5
rad/s. Old profiles keep their15.5 ceiling.16.5 is Unitree's12V no-load
reference, not proof of loaded capacity or an instantaneous hardware limiter.
Position differences also constrain the soft torque envelope. Body/force,
thermal, travel, IMU and communication guards remain. Default inert, one
finite explicit launch, no automatic retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_morning_supply import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_speed_window_v66',
    allow_wheel_speed_extension=True,
    wheel_speed_limit_rad_s=16.5,rise_wheel_speed_limit_rad_s=16.5,
    rise_speed_target_rad_s=15.5,abort_speed_trigger_rad_s=15.8,
    abort_target_limit_rad_s=16.0,
    active_message='SPEED_WINDOW_ACTIVE: 第49轮单次起身已启动，最多40秒；轮速软15.5、正常退出15.8、反馈停止16.5rad/s。初段目标400°/秒、反转0.08秒、净目标0.35Nm、70°C及原有行程/传感器/通信保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial49_returned_outward_after_travel_abort; retired launch, use reviewed successor'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-speed-window',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
