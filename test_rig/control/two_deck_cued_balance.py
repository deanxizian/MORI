#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Upright-only finite observation with a verified CAM red compensation cue.

Hand adjustment while mode0 keeps waiting instead of ending the trial. Close
to upright for250ms is enough; the fixed target and all armed guards remain.
No swing-up, automatic restart, unattended launch, or balance claim.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from net_torque_adapter import NetTorquePitchController
from two_deck_net_observe import PLAN as BASE

PLAN=dict(BASE,name='two_deck_red_cue_handheld_wait_v85',require_cam_indicator=True,
          handheld_wait=True,arm_stable_s=.25,arm_pitch_limit_deg=10.,
          arm_rate_limit_dps=15.,arm_pitch_span_deg=3.,
          wait_upright_message='WAIT_UPRIGHT: 红点熄灭，两轮停止。大致扶直即可，调整时继续等待；接近直立短暂停稳约0.25秒后接管。',
          active_message='CUED_BALANCE_ACTIVE: 平衡补偿开始，屏幕下方红点即将亮起；红点亮时只防倒，让轮子能滚动。最多30秒，停止时红点熄灭。')


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-cued',
                      controller=NetTorquePitchController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
