#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Upright zero-speed trial with small opposing wheel-rate corrections.

Uses the common +/- differential mixing structure of the inspected ArduPilot
skid mixer and MORI motion.c. This local rate-difference P is experimental;
it is not a full AP yaw estimator/controller. Preserve the common balance
request and every FF/net/feedback/travel/thermal guard. No automatic rearm.
"""
from air_trial import main as trial_main
from attitude import Fault,clip,finite
from ground_hold_trial import HoldTravel
from two_deck_zero_speed import PLAN as BASE,ZeroSpeedNetController

PLAN=dict(BASE,name='two_deck_zero_speed_small_wheel_sync_v87',
          control_phase='two_deck_synced_zero_speed_pid',
          sync_kp_nm_per_rad_s=.010,sync_filter_tau_s=.05,sync_limit_nm=.015,
          active_message='SYNCED_BALANCE_ACTIVE: 平衡补偿已开始，红点亮起。零速反馈加小幅两轮同步修正，最多30秒；请只防倒，允许车身和两轮小幅活动，原停止条件保留。')


class SynchronizedZeroSpeedController(ZeroSpeedNetController):
    def reset(self):
        super().reset()
        self.filtered_difference=0.
        self.sync_configuration=None

    def net_torque_requests(self,common,speeds,attitude,plan):
        config=tuple(plan[k] for k in ('sync_kp_nm_per_rad_s','sync_filter_tau_s','sync_limit_nm'))
        finite(*config)
        kp,tau,limit=config
        if not 0<=kp<=.02 or not .02<=tau<=.5 or not 0<=limit<=.015:
            raise Fault('wheel_sync_configuration_outside_plan')
        if self.sync_configuration is not None and config!=self.sync_configuration:
            raise Fault('wheel_sync_configuration_changed')
        self.sync_configuration=config
        difference=speeds[1]-speeds[0]
        dt=attitude['dt']
        weight=dt/(dt+tau)  # Same first-order form as the pinned AP low-pass.
        self.filtered_difference+=weight*(difference-self.filtered_difference)
        # Give pitch priority. Opposing corrections sum to zero and cannot
        # consume headroom beyond the original individual NET budget.
        margin=max(0.,min(limit,plan['predicted_net_torque_limit_nm']-abs(common)))
        correction=clip(kp*self.filtered_difference,margin)
        attitude['wheel_sync']=dict(rate_difference_right_minus_left_rad_s=difference,
            filtered_rate_difference_rad_s=self.filtered_difference,
            correction_nm=correction,available_margin_nm=margin,common_requested_net_nm=common)
        return {0:common+correction,1:common-correction}


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-synced',
                      controller=SynchronizedZeroSpeedController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
