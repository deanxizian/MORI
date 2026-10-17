#!/usr/bin/env python3
"""One gain comparison within unchanged wheel speed and net force budgets.

Keep trial56's0.06s transfer and15.5rad/s soft target. Gain0.15to0.25 permits
more torque below target and more braking above it. Position-difference
intersection, downstream0.35Nm predicted net budget,16.5filtered stop and all
body/capture/thermal/time/travel guards remain. No hardware clamp or successful
trajectory is inferred. Default inert, finite explicit launch, no retry/rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_medium_transfer import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery

PLAN=dict(RETIRED_PLAN,name='first_layer_governor_response_v74',rise_speed_gain_nm_per_rad_s=.25,
    active_message='GOVERNOR_RESPONSE_ACTIVE: 第57轮单次起身已启动，最多40秒；只把速度包络增益0.15改为0.25，目标15.5rad/s和净目标0.35Nm不变。反馈停止16.5rad/s、70°C及原有机身/传感器/通信/行程保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial57_reached17.892deg_but_no_capture; used entry retired before velocity-gate comparison'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-governor-response',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
