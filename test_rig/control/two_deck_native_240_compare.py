#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native0.240 comparison, retaining the v167 initial outer loop and guards.

Trial105's lower native damping did not reproduce quiet balance; its live
gyro windows were larger than trial104's selected native0.160 segment.
This profile changes only native damping0.080->0.240, with the same integer
NET allocator and full previous-rate compensation. It adds no host output
filter or wheel integrator. Sampled NET bounds are not an instantaneous
physical torque clamp. The physical outcome remains NOT_TESTED.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_080_compare import PLAN as BASE,NativeDampingController


START='--run-two-deck-native-240-compare'
PLAN=dict(BASE,name='two_deck_native_240_compare_v168',
    native_execution_kd=.240,control_phase='two_deck_native_240_compare',
    active_message='NATIVE240_COMPARE_ACTIVE: 自平衡补偿已开始，红点亮并响一声后手只防倒、先不推碰。主控保持P3.25/I0.60/D0.080/车速P0.20，只比较舵机本地阻尼0.240；最长30分钟。原0.12Nm、6rad/s、正负30度、80度及全部保护保留；红点灭、两声后接住。')


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeDampingController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
            socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeDampingController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
