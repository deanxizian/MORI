#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native0.36 comparison against the retained trial109 revision6 baseline.

Change only native execution damping0.24to0.36. The exact integer allocator
retains sampled NET/FF limits and every raw guard; these are not instantaneous
physical torque clamps. Host PID/reference/filter/timing remain unchanged.
Experimental inter-sample damping, not proof of reduced friction, backlash
or quiet balance. Default entry is inert; no automatic fault rearm.
"""
import json
import sys
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from two_deck_native_240_speed025 import PLAN as BASE,NativeDampingController
from live_tuning_policy import gains
START='--run-two-deck-native-360-compare'
PLAN=dict(BASE,name='two_deck_native_360_compare_v170',
    native_execution_kd=.360,control_phase='two_deck_native_360_compare',
    active_message='NATIVE360_COMPARE_ACTIVE: 自平衡补偿已开始，红点亮、一声后手只防倒，先不推碰。保持第109轮恢复后的P3.50/I0.60/D0.090/车速P0.25，只比较舵机本地阻尼0.240到0.360。最长30分钟；原0.12Nm采样预算、6rad/s、正负30度、80度和全部保护保留；红点灭、两声后接住。')
def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=NativeDampingController(channel),travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=NativeDampingController(channel),travel_factory=HoldTravel,description=__doc__)
if __name__=='__main__':raise SystemExit(main())
