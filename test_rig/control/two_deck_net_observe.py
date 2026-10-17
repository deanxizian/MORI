#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Thirty-second observation window; same v83 output mapping, gains and guards.

The two 10 s runs had essentially no body/wheel movement. The first was
explicitly hand-fixed; message delivery left little time in the second.
A longer finite window allows the operator to reduce support after ACTIVE.
No automatic rearm, unattended use, or claim of proven balance.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from net_torque_adapter import NetTorquePitchController
from two_deck_net_torque import PLAN as BASE

PLAN=dict(BASE,name='two_deck_net_torque_observe30_v84',duration_s=30.,
          active_message='NET_TORQUE_OBSERVE_ACTIVE: 平衡补偿已经开始，最多30秒。现在请让手不再承重，只准备接住车身，允许两轮小幅滚动。0.12Nm、4rad/s、20度、70度及原通信/转量条件保留，到时或异常停止。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-net-observe',
                      controller=NetTorquePitchController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
