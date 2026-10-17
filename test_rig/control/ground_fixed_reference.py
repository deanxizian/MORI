#!/usr/bin/env python3
"""Restrained observation around the same calibrated zero on every run.

Do not redefine the control target from the operator-held starting posture.
Use calibration-ground-01.json's geometric upright; it is still not a measured
center-of-mass balance point. All v8 gains and stop thresholds are retained.
"""
from air_trial import main as trial_main
from ground_trial import ground_command
from ground_hold_trial import HOLD_PLAN, HoldTravel


FIXED_PLAN=dict(
    HOLD_PLAN,name='restrained_ground_fixed_calibrated_reference_v9',
    capture_start_reference=False,
    wait_upright_message='WAIT_UPRIGHT: 两轮停止；请大致扶正。使用之前校准的固定直立零点，当前手扶姿态不会成为新目标。',
    active_message='RESTRAINED_GROUND_ACTIVE: 固定直立参考版开始，最多 30 秒；前后倾斜都向同一零点纠偏。只给很小的扰动，随后始终轻扶防倒，允许轮子小幅滚动。',
)


def main(argv=None):
    return trial_main(argv,plan=FIXED_PLAN,
                      start_flag='--run-restrained-ground-fixed-reference',
                      controller=ground_command,travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
