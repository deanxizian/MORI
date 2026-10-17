#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite one-factor speed-reference response comparison against v88.

Restore the v88 output path (no minimum-output shaping or common position
return). Shorten only the existing encoder-velocity LPF time constant from
0.20 to0.05s. Local experimental adaptation, not full ArduPilot firmware.
Keep the original1deg target bound,2deg/s slew, exact NET/FF budget and all
fault/stop lifecycle. The user-authorized6rad/s stop margin is retained.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_heading_hold import PLAN as BASE, RelativeHeadingController

PLAN=dict(BASE,name='two_deck_speed_reference_response_v93',duration_s=15.,
          wheel_speed_limit_rad_s=6.,speed_filter_tau_s=.05,
          control_phase='two_deck_speed_reference_response_pid',
          active_message='SPEED_RESPONSE_ACTIVE: 平衡补偿已开始，红点亮起，最多15秒。速度反馈滤波改为50ms；每轮FF/净输出预算仍0.12Nm、轮速6rad/s、20度、70度及原位移/通信保护。请只轻扶防倒，先不要推车。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-speed-response',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
