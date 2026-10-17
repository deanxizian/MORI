#!/usr/bin/env python3
"""Bounded body-rate/native-wheel-speed recovery candidate.

User confirmed inspection and return to the clear lying side after trial33.
Explicit finite-run flags remain required; no hardware I/O by default.
Uses the existing PID port, native S288 wheel loop, original hard limits and
latched fault stop. No automatic retry or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from self_righting_supervised import PLAN as RETIRED_PLAN,SupervisedRecovery


PLAN=dict(RETIRED_PLAN,
    name='first_layer_rate_reference_recovery_v51_1',duration_s=40.,stable_duration_s=30.,
    recovery_rate_max_dps=300.,recovery_settle_time_s=.15,
    recovery_rate_gain_nm_per_rad_s=.06,recovery_gravity_ff_nm=.18,
    pre_roll_target_rad_s=9.5,pre_roll_speed_limit_rad_s=13.,
    rise_speed_target_rad_s=14.,rise_speed_gain_nm_per_rad_s=.15,
    native_velocity_control=True,velocity_native_kd_nm_per_rad_s=.1,
    velocity_target_limit_rad_s=14.,velocity_target_slew_rad_s2=150.,
    # Match the near-upright slope of the recovery rate controller instead of
    # switching from a much softer rise loop to the historical 3 Nm/rad P.
    ap_kp=(.18+.06/.15)/.12,ap_kd=.06/.12,ap_ki=.05/.12,
    balance_friction_ff_nm=.05,balance_friction_soft_nm=.015,
    abort_on_fading_momentum=False,
    active_message='RATE_REFERENCE_RECOVERY_ACTIVE: 单次起身与稳定观察开始，最多 40 秒；机身速率软目标最多 300°/秒，轮速目标最多 14 rad/s；原 400°/秒、15.5 rad/s、0.35 Nm、70°C 及异常停止条件保留。目标连续稳定至少 30 秒，不自动重试。')

# The inherited older launch stays retired; only this reviewed successor is ready.
PLAN['motion_hold_reason']='trial34_overturn: retired native-velocity launch; use reviewed successor only'

def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-rate-reference-recovery',
        controller=SupervisedRecovery(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
