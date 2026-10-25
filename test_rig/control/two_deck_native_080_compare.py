#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compare native0.080 against trial104's selected outer-loop settings.

Trial104 did not establish sustained quiet. Retain its live P3.25/I0.60/
D0.080/speedP0.20 setting and compare only native damping0.160->0.080.
The0.15 speed-feedback experiment drifted and is not adopted. This is a
new physical comparison, not a demonstrated fix or proof of servo precision.
Keep full previous-rate compensation, original guards and explicit unlock.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_damping_stronger import StrongerNativeDampingController as NativeDampingController
from two_deck_native_damping_stronger_long import PLAN as BASE


START='--run-two-deck-native-080-compare'
PLAN=dict(BASE,name='two_deck_native_080_compare_v167',
    native_execution_kd=.080,ap_kd=.080/BASE['output_scale_nm'],
    speed_kp_rad_per_m_s=.20,control_phase='two_deck_native_080_compare',
    active_message='NATIVE080_COMPARE_ACTIVE: 自平衡补偿已开始，红点亮并响一声后手只防倒、先不推碰。保持上轮选用的P3.25/I0.60/D0.080/车速P0.20，对比舵机本地阻尼0.160到0.080，最长30分钟。原0.12Nm、6rad/s、正负30度、80度及全部保护保留；红点灭、两声后接住。')


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeDampingController(channel),
            travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,
            socket=SOCKET_PATH,motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,
            controller=NativeDampingController(channel),
            travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
