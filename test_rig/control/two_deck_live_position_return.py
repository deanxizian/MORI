#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite drift-return comparison on the original non-SMAX balance path.

Reuse the existing relative-position P -> speed -> pitch reference. Do not
add motor position stiffness or another actuator PID. Position is measured
relative to the case using nominal wheel radius, not world odometry. The
3cm/s cap is a reference cap, not an actual-speed limit. All original raw
guards, finite stop, state-preserving four-gain API and conditional I remain.
No automatic enable, boot service, origin reset during motion or fault rearm.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from stationary_integral import StationaryIntegralLiveController
from two_deck_live_stationary_integral import PLAN as BASE
from two_deck_position_hold import update_position_reference


START='--run-two-deck-live-position-return'
PLAN=dict(BASE,name='two_deck_live_position_return_v152',
    ap_kd=.070/BASE['output_scale_nm'],allow_position_velocity_target=True,
    position_speed_kp_per_s=.30,position_speed_limit_m_s=.03,
    active_message='POSITION_RETURN_LIVE_ACTIVE: 补偿已开始，红点亮、提示音一次。恢复原P/D，使用已有的编码器起点回中；回中速度目标最多3厘米每秒，非实际轮速限制。最多5分钟，原0.12Nm、6rad/s、正负30度、80度及其他保护保留；红点灭、两声后接住。')


class PositionReturnLiveController(StationaryIntegralLiveController):
    def reset(self):
        super().reset()
        self.position_origin=None
        self.position_configuration=None

    def __call__(self,attitude,speeds,plan=PLAN):
        self.allocations={}
        update_position_reference(self,attitude,speeds,plan)
        return super().__call__(attitude,speeds,plan)

    def extra_telemetry(self,sample):
        info=sample['attitude']['position_hold']
        return dict(super().extra_telemetry(sample),
            position_error_proxy_m=info['relative_error_proxy_m'],
            position_target_velocity_m_s=info['target_velocity_m_s'])


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=PositionReturnLiveController(
            TuningChannel(gains(PLAN))),travel_factory=HoldTravel,description=__doc__)
    channel=TuningChannel(gains(PLAN))
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,
                              motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=PositionReturnLiveController(channel),
                          travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
