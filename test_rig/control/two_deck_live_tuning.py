#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Supervised continuous balance with local online gains; maximum five minutes.

Start at selected v141 P3.25/zero-speedP0.25. Requests cannot change duration,
motion guards, travel budgets, output scale, calibration or actuator mode.
The existing timer/fault finalizer stops both wheels; no automatic rearm.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LiveTuningController,LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_trim_pitch_gain_325 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

START='--run-two-deck-live-tuning'
PLAN=dict(BASE,name='two_deck_live_tuning_v145',duration_s=300.,allow_live_tuning=True,
          control_phase='two_deck_live_tuning',
          active_message='LIVE_TUNING_ACTIVE: 连续平衡已开始，红点亮、提示音一次，单次最多5分钟。可在线平滑调整增益，不重启控制器；手只防倒，不推碰。每轮0.12Nm、6rad/s、正负30度、70度及原停止条件不变，任一触发即停止且不自动重启。结束两声和红点灭后接住。')


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=VelocityDiagnosticsController(),
                          travel_factory=HoldTravel,description=__doc__)
    channel=TuningChannel(gains(PLAN))
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,
                              motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=LiveTuningController(channel),
                          travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
