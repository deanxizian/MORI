#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Thirty-second native damping0.160 comparison with the v162 controller.

Keep full previous-rate compensation and the original outer loop and guards.
Only increase the native velocity coefficient from0.080 to0.160. The existing
integer allocator preserves the sampled NET budget, not instantaneous torque.
No host output filter, rate shaper, new integrator or automatic fault rearm.
Frozen command replay cannot predict physical settling or stability.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_damping_balance import PLAN as BASE,NativeDampingBalanceController


START='--run-two-deck-native-damping-stronger'
PLAN=dict(BASE,name='two_deck_native_damping_stronger_v165',
    native_execution_kd=.160,control_phase='two_deck_native_damping_stronger',
    active_message='NATIVE_STRONGER_DAMPING_ACTIVE: 自平衡补偿已开始，红点亮并响一声后手只防倒，先不推碰。本轮30秒，恢复完整轮速补偿和v162的P3.25/I0.60/D0.050/车速P0.25，只比较舵机本地速度阻尼0.080到0.160。不增加主控滤波或限斜率，原0.12Nm、6rad/s、正负30度、80度和全部异常保护保留；红点灭、两声后接住。')


class StrongerNativeDampingController(NativeDampingBalanceController):
    def extra_telemetry(self,sample):
        # Report the latched wire-allocation configuration, not the imported
        # v162 module's nominal0.080 label.
        return dict(super().extra_telemetry(sample),
            native_execution_kd=self.native_configuration[0])


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
