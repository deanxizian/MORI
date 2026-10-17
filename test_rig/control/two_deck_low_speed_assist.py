#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Small, continuous near-zero actuator assist on the v101/v98 baseline.

This is a local experimental S288 adapter, not ArduPilot friction-model
parity or a loaded-friction calibration. Preserve the AP-derived pitch PID,
velocity reference and exact FF/NET allocation. Trial30 was one unloaded
ramp per direction with nativeKd0.25, not the balanceKd0.005. At the first
sustained0.1deg/0.02rad/s onset, predicted NET magnitudes were approximately
0.0364/0.0074/0.0222/0.0499Nm for leftF/B,rightF/B. Choose at most one quarter,
rounded DOWN to whole mNm:0.009/0.001/0.005/0.012Nm. These are test settings,
not measured compensation values. Raw log SHA below preserves provenance.

Unlike rejectedv92's hard minimum, assistance is zero at zero request and
continuous through zero. It fades to zero at0.5rad/s and while opposing
motion faster than0.05rad/s. No history, integral, timed kick or automatic
retry is added. It uses only existing budget headroom, never raises it.
"""
import math

from air_trial import main as trial_main
from attitude import Fault,finite
from ground_hold_trial import HoldTravel
from two_deck_velocity_diagnostics import PLAN as BASE,VelocityDiagnosticsController


PLAN=dict(BASE,name='two_deck_smooth_low_speed_assist_v104',
          low_speed_assist_nm=((.009,.001),(.005,.012)),
          low_speed_assist_request_scale_nm=.020,
          low_speed_assist_fade_rad_s=.5,
          low_speed_assist_opposing_fade_rad_s=.05,
          low_speed_assist_evidence_sha256='1ec6d88c0309c8f405335b6622e680bf61dd3dd4527bb772ebb65fb1269c952f',
          control_phase='two_deck_low_speed_assist_diagnostics',
          active_message='LOW_SPEED_ASSIST_ACTIVE: 补偿已开始，红点亮起，最多30秒。原姿态参数加少量平滑起转辅助；轮子转起来后辅助退出。请全程不推碰、手只准备接住。每轮总命令仍最多0.12Nm，6rad/s、正负30度、70度及其他停止条件保留。')


def smooth_assist(request,speed,maximum,scale,fade_speed,opposing_speed,budget):
    """Memoryless Nm addition; original request still goes to the allocator."""
    if request==0.:return 0.
    direction=1. if request>0. else -1.
    near_zero=max(0.,1.-(abs(speed)/fade_speed)**2)**2
    opposing=max(0.,min(1.,1.+direction*speed/opposing_speed))
    addition=maximum*math.tanh(request/scale)*near_zero*opposing
    headroom=max(0.,budget-abs(request))
    return math.copysign(min(abs(addition),headroom),request)


class LowSpeedAssistController(VelocityDiagnosticsController):
    def reset(self):
        super().reset()
        self.assist_configuration=None

    def net_torque_requests(self,common,speeds,attitude,plan):
        maxima=plan['low_speed_assist_nm']
        if len(maxima)!=2 or any(len(pair)!=2 for pair in maxima):
            raise Fault('invalid_low_speed_assist_shape')
        scale=plan['low_speed_assist_request_scale_nm']
        fade=plan['low_speed_assist_fade_rad_s']
        opposing=plan['low_speed_assist_opposing_fade_rad_s']
        values=tuple(value for pair in maxima for value in pair)
        config=values+(scale,fade,opposing,plan['predicted_net_torque_limit_nm'])
        finite(*config)
        if (not all(0<=value<=.012 for value in values) or
                not .02<=scale<=.04 or not .25<=fade<=.5 or
                not .02<=opposing<=.05):
            raise Fault('low_speed_assist_outside_plan')
        if self.assist_configuration is not None and config!=self.assist_configuration:
            raise Fault('low_speed_assist_changed_during_run')
        self.assist_configuration=config
        original=super().net_torque_requests(common,speeds,attitude,plan)
        additions={mid:smooth_assist(request,speeds[mid],maxima[mid][0 if request>=0 else 1],
                    scale,fade,opposing,plan['predicted_net_torque_limit_nm'])
                   for mid,request in original.items()}
        result={mid:request+additions[mid] for mid,request in original.items()}
        attitude['low_speed_assist']=dict(original_net_requests_nm=original,
            additions_nm=additions,assisted_net_requests_nm=result.copy(),
            scope='experimental_partial_unloaded_onset_assist_not_calibrated_friction')
        return result


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-low-speed-assist',
        controller=LowSpeedAssistController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
