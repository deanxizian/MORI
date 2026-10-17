#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite position-return comparison with the existing pitch-frame velocity.

Only the speed-reference input changes from v152: reuse v105's timestamped
relative-wheel-plus-body-pitch calculation. This is nominal no-slip geometry,
not ArduPilot AHRS, calibrated floor speed or identified sensor delay. Raw
shaft feedback still owns actuator allocation, travel, heading and guards.
The earlier v105 trial drifted and was not adopted; this is a new comparison
on the current gain/trim/position baseline, not proof of that old trial.
No automatic enable, origin reset while active, boot service or fault rearm.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_live_position_return import PLAN as BASE,PositionReturnLiveController
from two_deck_pitch_velocity import PitchCorrectedVelocityReference


START='--run-two-deck-live-position-pitch-frame'
PLAN=dict(BASE,name='two_deck_live_position_pitch_frame_v153',duration_s=1800.,
    use_pitch_corrected_velocity=True,
    active_message='POSITION_PITCH_FRAME_ACTIVE: 补偿已开始，红点亮、提示音一次。保留回中层和原P/I/D，只校正车速中的车身俯仰分量。最多30分钟，原0.12Nm、6rad/s、正负30度、80度及所有转量和异常保护保留；红点灭、两声后接住。先不推碰。')


class PitchFramePositionReturnLiveController(PositionReturnLiveController):
    def reset(self):
        super().reset()
        self.speed_reference=PitchCorrectedVelocityReference()

    def extra_telemetry(self,sample):
        a=sample['attitude'];frame=a['velocity_frame_control']
        return dict(super().extra_telemetry(sample),
            pitch_velocity_frame_ready=frame['ready'],
            relative_encoder_velocity_proxy_m_s=a['velocity_hold']['encoder_velocity_proxy_m_s'],
            selected_control_velocity_proxy_m_s=frame['selected_control_proxy_m_s'])


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=PitchFramePositionReturnLiveController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,
                              motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=PitchFramePositionReturnLiveController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
