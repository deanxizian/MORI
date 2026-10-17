#!/usr/bin/env python3
"""Give native preparation setpoint1rad/s more room within the same budget.

Trial53 held8.7/9.1rad/s with10rad/s setpoints and did not reach9.5gate.
Change only native target cap to11, still below13preparation stop. Existing
net force budget,9.5both gate,0.4deadline and RISING torque path unchanged.
No guaranteed loaded tracking, hardware torque clamp or successful rise is
inferred. Default inert, one explicit finite launch, no retry/rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_velocity_preparation import PLAN as RETIRED_PLAN,VelocityPreparation

PLAN=dict(RETIRED_PLAN,name='first_layer_velocity_preparation_headroom_v71',
    preparation_velocity_target_limit_rad_s=11.,
    active_message='PREPARATION_HEADROOM_ACTIVE: 第54轮单次起身已启动，最多40秒；仅原生预滚目标上界10改为11rad/s，两轮达到9.5后切换。预滚13rad/s/0.4s、起身16.5rad/s、净目标0.35Nm、70°C及原有保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial54_failed_rise; retire used launch and withdraw native preparation experiment'


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-preparation-headroom',
        controller=VelocityPreparation(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
