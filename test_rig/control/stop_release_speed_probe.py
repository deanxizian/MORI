#!/usr/bin/env python3
"""One finite moderate-speed normal-release check, not self-righting.

Uses the reviewed low-speed probe's latched 25 degree / 2 second release.
Normal release ramps the velocity target down over 0.2 seconds first.
FF and position stiffness remain zero. Predicted net effort is capped at
0.12 Nm; native velocity target is at most 3 rad/s, with an independent
4 rad/s stop. All existing faults still lock both wheels; no automatic retry.
This check does not qualify stopping from the old 10--15 rad/s rise attempts.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from low_speed_stop_probe import make_plan,StopProbeController


PLAN=dict(make_plan('release',2.),
    name='normal_release_speed_probe_v48_ramp',pulse_ramp_s=.3,normal_decel_s=.2,
    velocity_target_limit_rad_s=3.,velocity_target_slew_rad_s2=10.,
    predicted_net_torque_limit_nm=.12,estimated_torque_limit_nm=.18,
    wheel_speed_limit_rad_s=4.,
    active_message='RELEASE_SPEED_PROBE_ACTIVE: 单次减速检查开始；轮速指令最多 3 rad/s、预测净目标最多 0.12 Nm；任一轮约 25°或 2 秒后，先用 0.2 秒逐步减速，再卸力、锁定。总转量仍受 3 cm 滚动折算限制；独立轮速线 4 rad/s、70°C 或异常立即锁定；不尝试起身。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-release-speed-probe',
        controller=StopProbeController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
