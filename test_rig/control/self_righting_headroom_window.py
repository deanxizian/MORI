#!/usr/bin/env python3
"""Finite rise window with unchanged hard actuator/body guards.

Trial43 began normal abandonment at approximately 33.5deg, while still moving
toward upright at105deg/s, because filtered wheel speed reached14rad/s. Give
the rise a further bounded speed window: soft target14.5, normal-exit trigger
14.8, native abort target15.0, independent hard stop15.5rad/s unchanged.
This is an empirical comparison, not a guarantee of available actuator torque.
All force, body-rate, temperature, travel, timing and sensor guards remain.
Default is inert; one explicit finite launch, no retry/rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_charged_compare import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,
    name='first_layer_headroom_window_v61',
    rise_speed_target_rad_s=14.5,
    abort_speed_trigger_rad_s=14.8,
    abort_target_limit_rad_s=15.0,
    active_message='HEADROOM_WINDOW_ACTIVE: 第44轮单次起身已启动，最多40秒。轮速软14.5、正常退出14.8、硬停止15.5rad/s；力矩、70°C及其他异常停止条件保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='operator_requested_overnight_pause_after_trial44: no launch during charging; physical supply/pose confirmation and reviewed successor required tomorrow'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-headroom-window',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
