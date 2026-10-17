#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite supervised output-encoder velocity comparison, not a qualified fix.

Use the actual ending v148 gains P3.25/I0.60/D0.085/speedP0.25. Only the
outer-loop velocity sensor changes; rotor safety/allocation/heading remain.
Default invocation is inert. No automatic restart or fault rearm.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from output_encoder_velocity import OutputVelocityLiveController
from two_deck_live_tuning_temp80 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

START='--run-two-deck-live-output-velocity'
PLAN=dict(BASE,name='two_deck_live_output_velocity_v149',duration_s=300.,
          ap_kd=.085/BASE['output_scale_nm'],use_output_encoder_velocity=True,
          active_message='OUTPUT_VELOCITY_ACTIVE: 补偿已开始，红点亮、提示音一次。零速反馈改用输出盘角度差分，再经过原50毫秒滤波；P3.25/I0.60/D0.085/车速P0.25。单次最多5分钟，0.12Nm、6rad/s、正负30度、80度及原净转量和异常条件保留；结束两声、红点灭后接住。')


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=VelocityDiagnosticsController(),
                          travel_factory=HoldTravel,description=__doc__)
    channel=TuningChannel(gains(PLAN))
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,
                              motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=OutputVelocityLiveController(channel),
                          travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
