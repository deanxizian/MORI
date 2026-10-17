#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite supervised conditional-integral comparison; default is inert.

Restore the original rotor-based velocity input. Near sensor-stationary
upright, reuse the existing AP integral anti-windup rule. P/D and every
actuator guard continue, no mode0 quiet state or automatic fault rearm.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from stationary_integral import StationaryIntegralLiveController
from two_deck_live_tuning_temp80 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController

START='--run-two-deck-live-stationary-integral'
PLAN=dict(BASE,name='two_deck_live_stationary_integral_v150',duration_s=300.,
          ap_kd=.085/BASE['output_scale_nm'],stationary_integral_guard=True,
          active_message='STATIONARY_INTEGRAL_ACTIVE: 补偿已开始，红点亮、提示音一次。恢复原车速反馈，接近静止时暂停积分继续增加，P/D纠偏保持。最多5分钟，原0.12Nm、6rad/s、正负30度、80度和其他保护保留；红点灭、两声提示后接住。')


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=VelocityDiagnosticsController(),
                          travel_factory=HoldTravel,description=__doc__)
    channel=TuningChannel(gains(PLAN))
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,
                              motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=StationaryIntegralLiveController(channel),
                          travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
