#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Add a small relative encoder-heading P to the existing rate damping.

This is common +/- differential PD mixing, using the difference of the two
signed shaft positions instead of a global heading estimate. It is only an
encoder-based heading proxy; slip and unequal tyre radii remain unmeasured.
Existing speed, posture and output budgets stay fixed. No automatic rearm.
"""
from air_trial import main as trial_main
from attitude import Fault,clip,finite
from ground_hold_trial import HoldTravel
from two_deck_synced_balance import PLAN as BASE,SynchronizedZeroSpeedController

PLAN=dict(BASE,name='two_deck_zero_speed_relative_heading_v88',
          control_phase='two_deck_heading_zero_speed_pid',
          include_wheel_position_feedback=True,heading_kp_nm_per_rad=.020,
          active_message='HEADING_BALANCE_ACTIVE: 平衡补偿已开始，红点亮起。零速反馈加左右累计位移差修正；仍最多30秒及原力矩、轮速、温度和倾角停止条件，请只轻扶防倒。')


class RelativeHeadingController(SynchronizedZeroSpeedController):
    def reset(self):
        super().reset()
        self.heading_origin=None
        self.heading_kp=None

    def net_torque_requests(self,common,speeds,attitude,plan):
        positions=attitude.get('wheel_position_forward_rad')
        if not isinstance(positions,dict) or set(positions)!={0,1}:
            raise Fault('relative_heading_requires_both_positions')
        kp=plan['heading_kp_nm_per_rad']
        finite(kp,*positions.values())
        if not 0<=kp<=.03:raise Fault('heading_gain_outside_plan')
        if self.heading_kp is not None and kp!=self.heading_kp:
            raise Fault('heading_gain_changed')
        self.heading_kp=kp
        difference=positions[0]-positions[1]
        if self.heading_origin is None:self.heading_origin=difference
        error=difference-self.heading_origin
        super().net_torque_requests(common,speeds,attitude,plan)
        info=attitude['wheel_sync']
        position_term=-kp*error
        rate_term=plan['sync_kp_nm_per_rad_s']*self.filtered_difference
        correction=clip(position_term+rate_term,info['available_margin_nm'])
        info.update(relative_position_error_rad=error,position_term_nm=position_term,
                    rate_term_nm=rate_term,correction_nm=correction,
                    heading_scope='relative_encoder_difference_not_global_heading')
        return {0:common+correction,1:common-correction}


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-heading',
                      controller=RelativeHeadingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
