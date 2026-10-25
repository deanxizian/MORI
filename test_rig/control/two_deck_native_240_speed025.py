#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Persist trial109 revision6 baseline as the native0.24 comparison reference.

Only retain its acknowledged live speedP0.25 in the initial plan; PID remains
P3.50/I0.60/D0.090. No timing, packet, allocation or guard changes. This is
not proof of quiet balance: the operator still reports rolling jerks. Default
entry is inert and no motor can automatically re-arm after a stop.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from two_deck_native_240_quiet import PLAN as BASE,NativeDampingController
from live_tuning_policy import gains
START='--run-two-deck-native-240-speed025'
PLAN=dict(BASE,name='two_deck_native_240_speed025_reference_v170',
    speed_kp_rad_per_m_s=.25,control_phase='two_deck_native_240_speed025',
    active_message='NATIVE240_SPEED025_ACTIVE: 自平衡补偿已开始，红点亮、一声后手只防倒，先不推碰。沿用第109轮恢复后的P3.50/I0.60/D0.090/车速P0.25/舵机本地阻尼0.240。最长30分钟；原0.12Nm采样预算、6rad/s、正负30度、80度和全部保护保留；红点灭、两声后接住。')
def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=NativeDampingController(channel),travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=NativeDampingController(channel),travel_factory=HoldTravel,description=__doc__)
if __name__=='__main__':raise SystemExit(main())
