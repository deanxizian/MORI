#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Duration/cue-only extension of the completed trial103 native controller.

Retain0.160 native damping, full previous-rate compensation, original
references, initial gains and raw guards. No host output filter, new wheel
loop, automatic enable or fault rearm. Longer observation is not proof of
rapid/repeatable quiet balance or physical actuator smoothness.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_damping_stronger import PLAN as BASE,StrongerNativeDampingController


START='--run-two-deck-native-damping-stronger-long'
PLAN=dict(BASE,name='two_deck_native_damping_stronger_long_v166',duration_s=1800.,
    control_phase='two_deck_native_damping_stronger_long',
    active_message='NATIVE_STRONGER_LONG_ACTIVE: 自平衡补偿已开始，红点亮并响一声后手只防倒、先不推碰。沿用上一轮完整控制和舵机本地阻尼0.160，最长30分钟，可在同一次站立中调整已允许的主控增益；原0.12Nm、6rad/s、正负30度、80度和全部异常保护保留。红点灭、两声后接住。')


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=StrongerNativeDampingController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
            socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=StrongerNativeDampingController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
