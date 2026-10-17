#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Opt in to bounded transient acceleration during active upright observation.

Reuse PitchEstimator's existing0.2to3g dynamic window, at most50ms outside
0.5to1.5g, gyro-only on those frames. Normal frames resume normal gravity
correction. No rotating-low-g exception, gain/output/other-guard change,
automatic rearm, or self-righting. Disabled and zero-arm remain strict.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_recovery_observe import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController

PLAN=dict(BASE,name='two_deck_bounded_push_transient_v96',
          active_imu_acceleration_transients=True,
          control_phase='two_deck_bounded_push_observation_pid',
          active_message='PUSH_OBSERVATION_ACTIVE: 补偿已开始，红点亮起，最多30秒。短时推碰加速度使用有界陀螺估计，正常后恢复重力修正；正负30度、0.12Nm命令、6rad/s、70度及其他停止保护保留。请先只防倒，等待轻推提示。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-push-observe',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
