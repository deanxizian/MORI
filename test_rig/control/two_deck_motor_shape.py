#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""10s motor-output study using the pinned ArduPilot throttle-min function.

Return to the operator-confirmed v88 pitch/speed/heading baseline; the common
position-return experiment is removed. Apply AP's exact percent shaping to
the common request before local differential allocation. This local Nm scale
and15% minimum are experimental, not calibrated vendor throttle parameters.
Zero remains zero; FF/net0.12Nm and all travel/temperature guards remain.
"""
from air_trial import main as trial_main
from attitude import Fault,clip,finite
from ground_hold_trial import HoldTravel
from offline_two_deck_review_20261016.motor_stage import scaled_throttle_pct
from two_deck_heading_hold import PLAN as BASE,RelativeHeadingController

PLAN=dict(BASE,name='two_deck_ap_minimum_output_v92',duration_s=10.,
          wheel_speed_limit_rad_s=6.,control_phase='two_deck_ap_motor_shape_pid',
          ap_motor_minimum_pct=15.,ap_motor_expo=0.,
          active_message='MOTOR_SHAPE_ACTIVE: ArduPilot最低输出函数对照开始，红点亮起，最多10秒。每轮FF/净输出预算仍0.12Nm、轮速6rad/s、20度、70度及原位移/通信保护；请只轻扶防倒。')


class MotorShapeController(RelativeHeadingController):
    def reset(self):
        super().reset()
        self.shaping_configuration=None

    def shape_common_net_request(self,requested,attitude,plan):
        config=tuple(plan[k] for k in ('ap_motor_minimum_pct','ap_motor_expo','output_scale_nm'))
        finite(*config,requested)
        minimum,expo,scale=config
        if not 0<=minimum<=15. or expo!=0. or scale!=plan['predicted_net_torque_limit_nm']:
            raise Fault('motor_shaping_configuration_outside_plan')
        if self.shaping_configuration is not None and config!=self.shaping_configuration:
            raise Fault('motor_shaping_configuration_changed')
        self.shaping_configuration=config
        pct=100.*clip(requested/scale,1.)
        output=scaled_throttle_pct(pct,minimum,expo)*.01*scale
        limited=abs(requested)>scale
        attitude['motor_shaping']=dict(pid_requested_net_nm=requested,
            input_pct=pct,minimum_pct=minimum,expo=expo,common_shaped_net_nm=output,
            input_limited=limited,
            scope='pinned_AP_get_scaled_throttle_percent_math_before_local_common_differential_mix',
            minimum_physically_calibrated=False)
        return output,limited


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-motor-shape',
                      controller=MotorShapeController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
