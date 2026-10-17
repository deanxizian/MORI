#!/usr/bin/env python3
"""One finite native-velocity-envelope comparison; inert unless explicitly run.

Same IMU state machine and body requests as v42. Map bounded net requests into
slewed native velocity targets. This is not a port of stepper gains or a proven
self-righting controller. Hard faults still lock both drives, with passive IMU.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_trial import SelfRightingController
from self_righting_lift_trial import LIFT_PLAN


VELOCITY_PLAN=dict(LIFT_PLAN,
    name='first_layer_self_righting_v43_native_velocity_envelope',
    native_velocity_control=True,velocity_native_kd_nm_per_rad_s=.060,
    velocity_target_limit_rad_s=11.,velocity_target_slew_rad_s2=150.,
    active_message='SELF_RIGHTING_ACTIVE: 原生速度环对照现在开始，最多 10 秒。速度指令限 11 rad/s，正常指令变化限 150 rad/s²，预测净力矩预算优先；无力矩前馈，预测净目标仍最多 0.35 Nm。原 15.5 rad/s、70°C 和其他故障停止条件保留；停止后继续被动记录，不自动重试。')


def main(argv=None):
    return trial_main(argv,plan=VELOCITY_PLAN,start_flag='--run-single-self-righting-velocity',
        controller=SelfRightingController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
