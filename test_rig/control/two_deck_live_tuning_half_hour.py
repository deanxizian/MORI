#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit supervised thirty-minute session with bounded online gain changes.

Keeps the same controller and instantaneous/net-travel guards. Full-rate raw
logging is retained; resource capacity must be checked before this long entry.
No boot enable, automatic restart or fault rearm.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LiveTuningController,LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_live_tuning_long import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

START='--run-two-deck-live-tuning-half-hour'
PLAN=dict(BASE,name='two_deck_live_tuning_half_hour_v147',duration_s=1800.,
          half_hour_live_session=True,rolling_path_limit_m=24.,
          active_message='LIVE_TUNING_ACTIVE: 连续平衡已开始，红点亮、提示音一次，单次最多30分钟。可在线平滑调参，不重启控制器；先自行站稳，红点仍亮时可做轻微短促扰动。每轮0.12Nm、6rad/s、正负30度、70度不变；累计往返折算最多24米，离起点净转量仍30厘米。保护或到时停止且不自动重启，结束两声和红点灭后接住。')


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
