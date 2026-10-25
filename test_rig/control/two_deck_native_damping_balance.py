#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native damping0.080 comparison against v160, without host torque filtering.

Trial97's2Nm/s common NET slew delayed reversals and did not maintain balance;
do not inherit that shaper. Keep v160's complete outer loop, initial gains,
references, live-status cap and original guards. Increase only native damping
from0.040 to0.080, with native rate reference recomputed by the same allocator.
The sampled NET request remains approximately unchanged. Inter-sample motor
behavior is experimental, not identified or qualified. No automatic rearm.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_causal_balance import NativeCausalBalanceController
from two_deck_native_observed_balance import PLAN as BASE,NativeObservedBalanceController


START='--run-two-deck-native-damping-balance'
PLAN=dict(BASE,name='two_deck_native_damping_balance_v162',duration_s=30.,
    native_execution_kd=.080,control_phase='two_deck_native_damping_balance',
    active_message='NATIVE_DAMPING_BALANCE_ACTIVE: 自平衡补偿已开始，红点亮并响一声后手只防倒、先不推碰。撤掉上轮力矩变化率限制，保持PID和原始目标，比较舵机原生速度阻尼0.040到0.080。最多30秒，原0.12Nm、6rad/s、正负30度、80度及全部异常保护保留；红点灭、两声后接住。')


class NativeDampingBalanceController(NativeObservedBalanceController):
    def extra_telemetry(self,sample):
        return dict(NativeCausalBalanceController.extra_telemetry(self,sample),
            **super().extra_telemetry(sample),native_execution_kd=PLAN['native_execution_kd'])


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
