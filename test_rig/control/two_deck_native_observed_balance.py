#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bound live-status copying, preserving v159 motor commands and guards.

Status returns only the latest eight 10-second windows, with explicit history
counts. Full raw reports and report summary history remain unchanged. Fixed
size PID/NET/velocity-target telemetry improves diagnosis; it adds no device
I/O and changes no controller law. Not a claim of realtime or quiet balance.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_causal_balance import PLAN as BASE,NativeCausalBalanceController


START='--run-two-deck-native-observed-balance'
PLAN=dict(BASE,name='two_deck_native_observed_balance_v160',
    live_status_window_limit=8,control_phase='two_deck_native_observed_balance',
    active_message='OBSERVED_BALANCE_ACTIVE: 自平衡补偿已开始。红点亮并响一声后，手只防倒，先不推碰。控制参数和电机执行沿用上一版启动值，限制实时状态历史的复制量。最多30分钟，原0.12Nm、6rad/s、正负30度、80度及全部异常保护保留；红点灭、两声后接住。')


class NativeObservedBalanceController(NativeCausalBalanceController):
    def extra_telemetry(self,sample):
        a=sample['attitude'];pid=a['ardupilot_balance']
        return dict(control_terms=dict(
            target_pitch_deg=pid['desired_pitch_forward_deg'],
            p_nm=pid['p_nm'],i_nm=pid['i_nm'],d_nm=pid['d_nm'],
            requested_net_nm=pid['requested_net_nm'],
            requested_per_wheel_nm=pid['requested_net_per_wheel_nm'].copy(),
            predicted_net_per_wheel_nm=pid['predicted_net_forward_nm'].copy(),
            native_velocity_target_rad_s=pid['native_velocity_forward_rad_s'].copy()))


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeObservedBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
            socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeObservedBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
