#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental same-window velocity input; unchanged pitch/actuator loops.

Compare with trial90's current P2.75/I0.60/D0.065/speedP0.25. Differentiate
continuous rotor/gear angle and interpolated body pitch over the same past
20ms window. This changes estimator bandwidth/delay, not verified floor
speed or calibrated internal servo latency. No independent output-angle
derivative, future samples, raw safety feedback replacement or fault rearm.
"""
import json
import sys

from air_trial import main as trial_main
from attitude import Fault
from causal_rotor_pitch_velocity import CausalRotorPitchVelocity
from ground_hold_trial import HoldTravel
from ground_velocity_hold import VelocityHoldController
from live_tuning import LocalTuningServer,TuningChannel,SOCKET_PATH
from live_tuning_policy import gains
from offline_after24_20261017.pitch_velocity_proxy import PitchVelocityProxy
from two_deck_live_quiet_baseline import PLAN as BASE,PitchFramePositionReturnLiveController


START='--run-two-deck-live-causal-velocity'
PLAN=dict(BASE,name='two_deck_live_causal_velocity_v157',ap_kd=.065/BASE['output_scale_nm'],
    use_causal_rotor_pitch_velocity=True,causal_velocity_window_s=.020,
    active_message='CAUSAL_VELOCITY_ACTIVE: 平衡补偿已开始，红点亮、提示音一次。保持当前P2.75/I0.60/D0.065/车速P0.25，仅比较统一20毫秒过去窗口的速度估计。最多30分钟，原0.12Nm、6rad/s、正负30度、80度及全部通信/转量保护不变。红点亮后手只防倒，先不推碰；红点灭、两声后接住。')


class CausalVelocityReference(VelocityHoldController):
    def __init__(self):
        super().__init__();self.estimator=None;self.configuration=None
        self.warmup=PitchVelocityProxy()

    def velocity_proxy(self,a,speeds,plan):
        if plan.get('use_causal_rotor_pitch_velocity') is not True:
            raise Fault('causal_velocity_explicit_opt_in_required')
        config=(plan['nominal_wheel_radius_m'],plan['causal_velocity_window_s'],plan['loop_gap_s'])
        if config!=(.04,.020,.025):raise Fault('causal_velocity_profile_outside_review')
        if self.configuration is not None and config!=self.configuration:
            raise Fault('causal_velocity_configuration_changed')
        try:
            if self.estimator is None:
                self.estimator=CausalRotorPitchVelocity(radius_m=config[0],window_s=config[1],max_gap_s=config[2])
                self.configuration=config
            r=self.estimator.update(a['t'],a['pitch_deg'],a.get('wheel_position_forward_rad',{}),
                a.get('wheel_feedback_received_monotonic',{}),speeds)
            if r['ready']:proxy=r['corrected_proxy_m_s']
            else:
                # Explicit startup only, about six200Hz frames in trial87.
                # Reuse the unchanged baseline input until the past window
                # exists. Once ready, estimator failure faults, never falls back.
                old=self.warmup.update(a['t'],a['pitch_rate_dps'],speeds,
                    a.get('wheel_feedback_received_monotonic',{}))
                proxy=old['corrected_proxy_m_s'] if old['ready'] else old['raw_proxy_m_s']
        except ValueError as exc:raise Fault('causal_velocity_'+str(exc)) from exc
        a['velocity_frame_control']=dict(r,selected_control_proxy_m_s=proxy,
            legacy_startup_warmup=not r['ready'],internal_sensor_latency_calibrated=False)
        return proxy


class CausalVelocityLiveController(PitchFramePositionReturnLiveController):
    def reset(self):
        super().reset()
        self.arm_speed_reference=self.speed_reference
        self.speed_reference=CausalVelocityReference()

    def validate_arm(self,a,speeds,plan):
        # Preserve the complete existing raw/PID/legacy-reference arming
        # validation. The new estimator is used only after the runner's
        # mandatory reset-before-active, with fresh successful motor pairs.
        active=self.speed_reference;self.speed_reference=self.arm_speed_reference
        try:return super().validate_arm(a,speeds,plan)
        finally:self.speed_reference=active


def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv);channel=TuningChannel(gains(PLAN))
    if START not in args:
        return trial_main(args,plan=PLAN,start_flag=START,controller=CausalVelocityLiveController(channel),
                          travel_factory=HoldTravel,description=__doc__)
    with LocalTuningServer(channel):
        print(json.dumps(dict(kind='LOCAL_TUNING_READY',session=channel.session,socket=SOCKET_PATH,
                              motor_enable_authority=False)),flush=True)
        return trial_main(args,plan=PLAN,start_flag=START,controller=CausalVelocityLiveController(channel),
                          travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
