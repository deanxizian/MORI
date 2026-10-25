#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Longer observation of trial98's unchanged native damping controller.

Only duration and entry/cue labels differ. Keep0.080 native damping and
all v162 gains, references and guards. This is an observation, not proven
repeatable rapid quiet balance. Default invocation performs no hardware I/O.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_damping_balance import PLAN as BASE,NativeDampingBalanceController


START='--run-two-deck-native-damping-long-balance'
PLAN=dict(BASE,name='two_deck_native_damping_long_balance_v163',duration_s=1800.,
    control_phase='two_deck_native_damping_long_balance',
    active_message='NATIVE_DAMPING_LONG_ACTIVE: 自平衡补偿已开始。红点亮并响一声后手只防倒、先不推碰。保持上一轮完整控制与原生速度阻尼0.080，最长30分钟，可在同一次站立中调整已允许的主控增益；原0.12Nm、6rad/s、正负30度、80度及全部异常保护保留。红点灭、两声后接住。')


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeDampingBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
            socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeDampingBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
