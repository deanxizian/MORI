#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Cold-start candidate using trial106's user-confirmed quiet live gains.

Retain native0.240, the same NET allocator and every v168 raw guard. Only
persist P3.50/I0.60/D0.090/speedP0.15 as initial gains. Trial106 established
unsupported warm-run stillness, not rapid cold-start settling or controlled
push recovery. Its serial Write timeout remains unresolved; write diagnostics
add timestamps without retrying, extending deadlines or changing packets.
"""
import json
import sys

from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from two_deck_native_240_compare import PLAN as BASE,NativeDampingController

START='--run-two-deck-native-240-quiet'
PLAN=dict(BASE,name='two_deck_native_240_quiet_v169',
    ap_kp=3.50/BASE['output_scale_nm'],ap_kd=.090/BASE['output_scale_nm'],
    speed_kp_rad_per_m_s=.15,control_phase='two_deck_native_240_quiet',
    active_message='NATIVE240_QUIET_ACTIVE: 自平衡补偿已开始，红点亮并响一声后手只防倒、先不推碰。采用上轮无接触停住时的P3.50/I0.60/D0.090/车速P0.15/本地阻尼0.240，最长30分钟。原0.12Nm、6rad/s、正负30度、80度及全部保护不变；红点灭、两声后接住。')


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
