#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite upright P/D response comparison with explicit NET torque semantics.

Experimental physical P is reduced3 to1.5Nm/rad; I0.6 and D0.05 are retained.
This is a new actuator mapping plus a lower-P candidate, not a single-factor
plant identification, vendor preset, calibrated gain set or balance proof.
No I/O by default, no self-righting, no automatic fault re-arm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from net_torque_adapter import NetTorquePitchController
from two_deck_lower_damping import PLAN as BASE

PLAN=dict(BASE,name='two_deck_net_torque_lower_p_v83',
          control_phase='two_deck_net_torque_pid',ap_kp=1.5/.12,
          active_message='NET_TORQUE_BALANCE_ACTIVE: 两轮平衡补偿现在开始，最多10秒。请轻扶防倒并允许小幅滚动；到时或异常会停止。0.12Nm、4rad/s、20度、70度及原通信/转量条件保留。')
PLAN.pop('motion_hold_reason')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-net-torque',
                      controller=NetTorquePitchController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
