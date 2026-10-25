#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Same native0.36 baseline with a larger explicit live posture-D range.

Initial P3.50/I0.60/D0.090/speed0.25/native0.36 remain unchanged. v171's
bringup policy permits D up to0.150 in existing <=0.015/transaction ramps;
no initial high-D command or other gain/guard expansion. It does not claim
physical settling or alter the pinned ArduPilot PID implementation. Default
entry is inert and faults never automatically re-arm.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from two_deck_native_360_compare import PLAN as BASE,NativeDampingController
from live_tuning_policy import gains
START='--run-two-deck-native-360-d-tuning'
PLAN=dict(BASE,name='two_deck_native_360_d_tuning_v171',
    control_phase='two_deck_native_360_d_tuning',
    active_message='NATIVE360_D_TUNING_ACTIVE: 自平衡补偿已开始，红点亮、一声后手只防倒，先不推碰。保持P3.50/I0.60/D0.090/车速P0.25/舵机本地阻尼0.360，接下来在同一次站立中小步比较更强的姿态阻尼。最长30分钟；原0.12Nm采样预算、6rad/s、正负30度、80度和全部保护保留；红点灭、两声后接住。')
def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=NativeDampingController(channel),travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=NativeDampingController(channel),travel_factory=HoldTravel,description=__doc__)
if __name__=='__main__':raise SystemExit(main())
