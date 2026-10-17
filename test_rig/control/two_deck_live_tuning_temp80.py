#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Supervised thirty-minute entry with the user-selected 80 C case-temperature stop.

Only the host temperature threshold changes from v147. Vendor fault/warning
checks remain authoritative; no claim of continuous thermal qualification.
Default invocation is inert. No automatic restart or live guard modification.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LiveTuningController,LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_live_tuning_half_hour import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

START='--run-two-deck-live-tuning-temp80'
PLAN=dict(BASE,name='two_deck_live_tuning_temp80_v148',temperature_limit_c=80,
          active_message='LIVE_TUNING_ACTIVE: 连续平衡已开始，红点亮、提示音一次，单次最多30分钟。可在线平滑调参；温度反馈达到80度或电机报错即停止。每轮0.12Nm、6rad/s、正负30度、累计往返24米、净转量30厘米和其他停止条件保留。保护或到时停止，不自动重启；结束两声和红点灭后接住。')


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
