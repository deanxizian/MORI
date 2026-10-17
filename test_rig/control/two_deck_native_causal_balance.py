#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actuator-execution comparison on the current causal/position baseline.

Keep the current P3.25/I0.60/D0.050/speedP0.25, references, raw guards and
state lifecycle. Reuse the reviewed native velocity NET allocator with
Kd0.040, between the old passive0.005 and the previously exercised0.40
native execution. This is experimental, not an identified actuator model.
Sampled predicted NET is not an instantaneous hardware torque clamp.
Default invocation never opens devices; no automatic fault rearm.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_live_causal_velocity import PLAN as BASE,CausalVelocityLiveController
from two_deck_native_execution import NativeExecutionController


START='--run-two-deck-native-causal-balance'
PLAN=dict(BASE,name='two_deck_native_causal_balance_v159',
    ap_kp=3.25/BASE['output_scale_nm'],ap_kd=.050/BASE['output_scale_nm'],
    native_execution_kd=.040,native_execution_speed_limit_rad_s=6.,
    control_phase='two_deck_native_causal_balance',
    active_message='NATIVE_CAUSAL_BALANCE_ACTIVE: 自平衡补偿已开始，红点亮并响一声后，手只防倒。主控P3.25/I0.60/D0.050/车速P0.25保持，比较舵机内部速度阻尼执行。最多30分钟，原0.12Nm、6rad/s、正负30度、80度及全部异常保护保留；先不推碰。红点灭、两声后接住。')


class NativeCausalBalanceController(NativeExecutionController,CausalVelocityLiveController):
    """Existing execution wrapper around the complete causal/live controller.

    C3 order is NativeExecution -> Causal/Position/Live -> original PID.
    The wrapper replaces allocations only after the unchanged outer call.
    Zero-arm still uses the original explicit zero packet path; the runner
    resets all un-applied controller state before the first active pair.
    """


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeCausalBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
                              socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeCausalBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
