#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fresh-start comparison of the gains actually exercised in trial86.

Reuse v153's complete controller, frame estimator, origin return and fault
lifecycle. Only initial pitch P/D change to the live-exercised 2.75/0.050.
Trial86 had finite quiet intervals and two light pushes, but did not prove
rapid/repeatable settling. Suspended native-speed continuity does not
qualify loaded accuracy, friction or backlash. No motor PID/backend change.
No automatic enable, service, controller reset or fault rearm.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_live_position_pitch_frame import PLAN as BASE,PitchFramePositionReturnLiveController


START='--run-two-deck-live-quiet-baseline'
PLAN=dict(BASE,name='two_deck_live_quiet_baseline_v154',
    ap_kp=2.75/BASE['output_scale_nm'],ap_kd=.050/BASE['output_scale_nm'],
    active_message='QUIET_BASELINE_ACTIVE: 补偿已开始，红点亮、提示音一次。从启动即使用P2.75/I0.60/D0.050/车速P0.25，检验能否更快收住；控制方式和原有保护不变。最多30分钟，仍为0.12Nm、6rad/s、正负30度、80度及全部通信/转量保护。先不推碰；红点灭、两声后接住。')


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
