#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental 2Nm/s common NET slew, before the native wire allocation.

The first active command is unchanged. Subsequent bounded common NET requests
approach the PID request at no more than2Nm/s, retaining differential control,
all raw motion/health guards and the sampled0.12Nm/FF budget. This introduces
tracking lag and is not a proven improvement in balance or loaded smoothness.
Native velocity is not independently filtered: that would alter hybrid NET.
No default hardware I/O, hot reload or automatic fault rearm.
"""
import json
import sys

from air_trial import main as trial_main
from attitude import Fault,finite,clip
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_causal_balance import NativeCausalBalanceController
from two_deck_native_observed_balance import PLAN as BASE,NativeObservedBalanceController


START='--run-two-deck-native-smooth-balance'
PLAN=dict(BASE,name='two_deck_native_smooth_balance_v161',duration_s=30.,
    common_net_slew_nm_s=2.,control_phase='two_deck_native_smooth_balance',
    active_message='SMOOTH_BALANCE_ACTIVE: 平衡补偿已开始，红点亮并响一声后手只防倒，先不推碰。本轮30秒，保持PID和200Hz目标采样，仅比较力矩目标2Nm/s变化率约束。原0.12Nm、6rad/s、正负30度、80度及全部异常保护保留；红点灭、两声后接住。')


class NativeSmoothBalanceController(NativeObservedBalanceController):
    def reset(self):
        super().reset()
        self.slew_configuration=None
        self.slew_time=None
        self.slew_output=None

    def shape_common_net_request(self,requested,attitude,plan):
        config=(plan.get('common_net_slew_nm_s'),plan['predicted_net_torque_limit_nm'])
        if any(type(x) not in (int,float) for x in config):
            raise Fault('invalid_common_net_slew_configuration')
        finite(*config,requested,attitude['t'])
        if config!=(2.,.12):raise Fault('common_net_slew_outside_review')
        if self.slew_configuration is not None and config!=self.slew_configuration:
            raise Fault('common_net_slew_configuration_changed')
        self.slew_configuration=config
        wanted=clip(requested,config[1]);t=attitude['t']
        first=self.slew_time is None
        if first:
            output=wanted
        else:
            dt=t-self.slew_time
            if not .001<=dt<=.025:raise Fault('invalid_common_net_slew_gap')
            output=self.slew_output+clip(wanted-self.slew_output,config[0]*dt)
        slew_limited=abs(output-wanted)>1e-12
        attitude['net_command_slew']=dict(pid_requested_net_nm=requested,
            bounded_target_nm=wanted,common_output_nm=output,
            slew_limited=slew_limited,budget_limited=wanted!=requested,
            maximum_rate_nm_s=config[0],first_command_unchanged=first,
            scope='Common NET before differential mix, not per-wheel instantaneous hardware torque')
        self.slew_time=t;self.slew_output=output
        return output,slew_limited or wanted!=requested

    def __call__(self,attitude,speeds,plan):
        commands=super().__call__(attitude,speeds,plan)
        # Native allocation must not hide shaping saturation from next-cycle
        # integrator admission and the live gain-update window.
        s=attitude['net_command_slew']
        self.previous_limited|=s['slew_limited'] or s['budget_limited']
        attitude['ardupilot_balance']['adapter_limited']=self.previous_limited
        return commands

    def extra_telemetry(self,sample):
        return dict(NativeCausalBalanceController.extra_telemetry(self,sample),
            **super().extra_telemetry(sample),
            command_slew=sample['attitude']['net_command_slew'].copy())


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeSmoothBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
            socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeSmoothBalanceController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
