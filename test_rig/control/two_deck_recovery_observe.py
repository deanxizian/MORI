#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""30s upright recovery observation; no swing-up or automatic rearm.

Restore the physically completed v93 controller (velocity gain0.25, LPF50ms),
not the untested doubled gain. Widen active pitch stop20to30deg. Command/NET
remain0.12Nm; active estimate guard allows0.13Nm with50ms dwell and a0.15Nm
instant ceiling. All other guards and original mode0/zero-arm limits remain.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_speed_response import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController

PLAN=dict(BASE,name='two_deck_upright_recovery_observation_v95',duration_s=30.,
          pitch_limit_deg=30.,active_torque_feedback_guard=True,
          torque_feedback_soft_nm=.13,torque_feedback_hard_nm=.15,
          torque_feedback_dwell_s=.05,
          control_phase='two_deck_upright_recovery_observation_pid',
          active_message='RECOVERY_OBSERVATION_ACTIVE: 补偿已开始，红点亮起，最多30秒。倾角退出线正负30度，FF/净命令仍0.12Nm；反馈超过0.13Nm持续50ms或单帧超过0.15Nm才按力矩退出。轮速6rad/s、70度及原通信/位移保护仍在。请先只防倒，等待轻推提示。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-recovery-observe',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
