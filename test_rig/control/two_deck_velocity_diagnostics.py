#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reviewed v98 baseline plus shadow velocity-frame diagnostics.

The diagnostic estimate is never fed back into pitch control, allocation,
travel guards or motor packets. Control remains v98. After-charge restart:
the user confirmed charger disconnected and upright catch-only guarding;
mode-0 preflight passed. Every run still requires the explicit entry flag,
operator readiness, pinned sources/calibration and fresh runtime checks.
No automatic restart or fault rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from two_deck_drive_headroom import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController
from offline_after24_20261017.pitch_velocity_proxy import PitchVelocityProxy


PLAN=dict(BASE,name='two_deck_velocity_frame_diagnostics_v101',
          use_wheel_feedback_timestamps=True,
          control_phase='two_deck_velocity_frame_diagnostics',
          active_message='VELOCITY_DIAGNOSTICS_ACTIVE: 补偿已开始，红点亮起，最多30秒。使用之前v98参数，同时记录车身转动对编码器车速的影响；诊断估计不参与控制。这轮不推碰，手只防倒，原0.12Nm、6rad/s、正负30度、70度和其他停止条件保留。')


class VelocityDiagnosticsController(RelativeHeadingController):
    def reset(self):
        super().reset()
        self.velocity_study=PitchVelocityProxy()

    def __call__(self,attitude,speeds,plan=PLAN):
        commands=super().__call__(attitude,speeds,plan)
        try:
            diagnostic=self.velocity_study.update(attitude['t'],attitude['pitch_rate_dps'],
                speeds,attitude.get('wheel_feedback_received_monotonic',{}))
        except ValueError as exc:
            # Existing raw health/timing guards still own motor admission.
            # A shadow estimate is neither a control input nor new authority.
            diagnostic=dict(ready=False,status='INVALID',reason=str(exc),
                            corrected_proxy_m_s=None)
            self.velocity_study=PitchVelocityProxy()
        attitude['velocity_frame_diagnostics']=diagnostic
        return commands


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-velocity-diagnostics',
        controller=VelocityDiagnosticsController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
