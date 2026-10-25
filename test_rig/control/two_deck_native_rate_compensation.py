#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Retain25% of native damping instead of cancelling all measured shaft rate.

The existing allocator sets native_target = previous_rate + NET/Kd, modulo
wire quantization and limits. Requesting NET = outer_request - Kd*.25*rate
therefore changes it to .75*previous_rate + outer_request/Kd. This reduces
raw-rate feedthrough without a host output filter. It adds real shaft-rate
damping, changes the closed-loop dynamics and is not a proven improvement.
Shaft-relative rate is not floor speed. All raw guards and sampled budgets
remain authoritative; no additional motor PID, default I/O or fault rearm.
"""
import json
import math
import sys

from air_trial import main as trial_main
from attitude import Fault,finite
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from protocol import RATIO
from two_deck_native_damping_balance import PLAN as BASE,NativeDampingBalanceController


START='--run-two-deck-native-rate-compensation'
PLAN=dict(BASE,name='two_deck_native_rate_compensation_v164',
    ap_kp=3.0/BASE['output_scale_nm'],native_rate_compensation_fraction=.75,
    control_phase='two_deck_native_rate_compensation',
    active_message='RATE_COMPENSATION_ACTIVE: 自平衡补偿已开始，红点亮并响一声后手只防倒，先不推碰。本轮30秒，保持当前P3.0/I0.60/D0.050/车速P0.25和原生阻尼0.080，比较将上一拍轮速进入速度目标的比例从100%降到75%。不增加主控输出滤波，原0.12Nm、6rad/s、正负30度、80度及全部异常保护保留；红点灭、两声后接住。')


class NativeRateCompensationController(NativeDampingBalanceController):
    def reset(self):
        super().reset()
        self.rate_compensation_configuration=None

    def net_torque_requests(self,common,speeds,attitude,plan):
        fraction=plan.get('native_rate_compensation_fraction')
        if type(fraction) not in (int,float):
            raise Fault('invalid_native_rate_compensation')
        kd=plan['native_execution_kd'];finite(fraction,kd)
        config=(fraction,kd)
        if config!=(.75,.080):raise Fault('native_rate_compensation_outside_review')
        if self.rate_compensation_configuration is not None and config!=self.rate_compensation_configuration:
            raise Fault('native_rate_compensation_changed')
        self.rate_compensation_configuration=config
        original=super().net_torque_requests(common,speeds,attitude,plan)
        # Match the exact native wire Kd rather than its rounded plan label.
        kd_step=RATIO**2/128000000.
        exact_kd=math.floor(kd/kd_step)*kd_step
        retained=exact_kd*(1.-fraction)
        result={mid:request-retained*speeds[mid] for mid,request in original.items()}
        attitude['native_rate_compensation']=dict(
            fraction=fraction,retained_shaft_damping_nm_per_rad_s=retained,
            before_per_wheel_nm=original.copy(),
            damping_per_wheel_nm={m:-retained*v for m,v in speeds.items()},
            after_per_wheel_nm=result.copy(),
            scope='Previous shaft-relative feedback, not measured floor speed or instantaneous torque')
        return result

    def extra_telemetry(self,sample):
        info=sample['attitude']['native_rate_compensation']
        return dict(super().extra_telemetry(sample),
            native_rate_compensation_fraction=info['fraction'],
            retained_shaft_damping_nm_per_rad_s=info['retained_shaft_damping_nm_per_rad_s'])


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeRateCompensationController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
            socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeRateCompensationController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
