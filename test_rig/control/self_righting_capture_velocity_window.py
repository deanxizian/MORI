#!/usr/bin/env python3
"""Permit a bounded handoff at0.6m/s wheel-derived rolling estimate.

Trial57 reached17.892deg and-28.244deg/s at0.5812m/s, failing only the0.5
capture-speed gate. Change it to0.6; all angle/rate, hard speed, torque and
travel guards remain. Stable success still requires the same30s ending
window, not a CAPTURE label. Wheel speed is not independently measured ground
speed. Default inert, one finite explicit launch, no retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_governor_response import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_capture_velocity_window_v75',capture_velocity_m_s=.6,
    active_message='CAPTURE_VELOCITY_WINDOW_ACTIVE: 第58轮单次起身已启动，最多40秒；只把接管速度门限0.5改为0.6m/s，18度/120度每秒门限和至少30秒稳定标准不变。轮速16.5rad/s硬停止、净目标0.35Nm、70°C及原有保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial58_physical_FAIL; all motion entries held during disabled200Hz timing qualification'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-capture-velocity-window',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
