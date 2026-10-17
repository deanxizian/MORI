#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One-factor lower pitch-P comparison, no actuator/backend/guard changes.

Trial87 showed continued low-speed/burst response with P dominating command
RMS. Partial loaded native-rate feedback was more continuous, but the body
tilted and reverse was not reached: no friction/backlash/accuracy diagnosis.
Start P2.50 instead of2.75; retain I0.60/D0.050/speedP0.25. The explicitly
reviewed online P range extends down to2.00 with unchanged0.25 step and
1-5s ramp. No silent state reset, automatic enable/retry/fault rearm.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_live_quiet_baseline import PLAN as BASE,PitchFramePositionReturnLiveController


START='--run-two-deck-live-lower-pitch-gain'
PLAN=dict(BASE,name='two_deck_live_lower_pitch_gain_v156',ap_kp=2.50/BASE['output_scale_nm'],
    active_message='LOWER_PITCH_GAIN_ACTIVE: 平衡补偿已开始，红点亮、提示音一次。姿态P由2.75降到2.50，I0.60/D0.050/车速P0.25及原控制方式不变；可按每步最多0.25平滑试到P2.00。最多30分钟，0.12Nm、6rad/s、正负30度、80度及全部通信/转量保护保留。红点亮后手只防倒，先不推碰；红点灭、两声后接住。')


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
