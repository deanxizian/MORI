# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental output-shaft velocity input; no I/O or actuator authority.

S288 OutPos is the independent output sensor (13 bits per turn). Keep rotor
feedback for native damping, torque allocation and existing safety checks.
Host timestamp differences do not identify sensor-internal acquisition delay.
"""
import math
from attitude import Fault,finite
from ground_velocity_hold import VelocityHoldController
from live_tuning import LiveTuningController


class OutputEncoderRates:
    def __init__(self):
        self.previous={};self.position={0:0.,1:0.};self.rates=None;self.times={}

    def observe(self,feedback,signs):
        if set(feedback)!={0,1} or signs!={0:1,1:-1}:
            raise Fault('output_encoder_requires_both_calibrated_wheels')
        next_previous={};next_position={};rates={};times={}
        for mid in (0,1):
            row=feedback[mid]
            angle=row['absolute_output_rad'];rotor=row['position_rad']
            t=row['feedback_received_monotonic'];finite(angle,rotor,t)
            if not 0<=angle<math.tau:raise Fault('output_encoder_angle_outside_turn')
            if mid in self.previous:
                old_angle,old_rotor,old_t=self.previous[mid];dt=t-old_t
                if not .001<=dt<=.025:raise Fault('output_encoder_feedback_gap')
                delta=(angle-old_angle+math.pi)%math.tau-math.pi
                rotor_delta=rotor-old_rotor
                # 8deg is a declared gross-jump diagnostic allowance after
                # observed3-6deg relative discrepancies, not rated backlash.
                if abs(delta-rotor_delta)>math.radians(8):
                    raise Fault('output_encoder_inconsistent_step')
                rates[mid]=signs[mid]*delta/dt
                next_position[mid]=self.position[mid]+signs[mid]*delta
            else:next_position[mid]=0.
            next_previous[mid]=(angle,rotor,t);times[mid]=t
        self.previous=next_previous;self.position=next_position;self.times=times
        self.rates=rates if set(rates)=={0,1} else None

    def velocity(self,t,radius):
        finite(t,radius)
        if self.rates is None:return None
        if any(not 0<=t-stamp<=.015 for stamp in self.times.values()):
            raise Fault('output_encoder_stale_or_future_feedback')
        return radius*(self.rates[0]+self.rates[1])/2


class OutputVelocityReference(VelocityHoldController):
    def __init__(self,tracker):
        super().__init__();self.tracker=tracker

    def velocity_proxy(self,attitude,speeds,plan):
        if plan.get('use_output_encoder_velocity') is not True:
            raise Fault('output_encoder_requires_explicit_opt_in')
        proxy=self.tracker.velocity(attitude['t'],plan['nominal_wheel_radius_m'])
        ready=proxy is not None
        if not ready:proxy=super().velocity_proxy(attitude,speeds,plan)
        attitude['output_velocity_input']=dict(ready=ready,
            raw_output_velocity_proxy_m_s=proxy if ready else None,
            selected_velocity_proxy_m_s=proxy,
            warmup_rotor_proxy=not ready,
            scope='output_encoder_difference_before_existing50ms_filter_not_floor_speed')
        return proxy


class OutputVelocityLiveController(LiveTuningController):
    def reset(self):
        super().reset()
        self.output_tracker=OutputEncoderRates()
        self.speed_reference=OutputVelocityReference(self.output_tracker)
        self.output_active_calls=0

    def __call__(self,attitude,speeds,plan):
        if self.output_active_calls>=2 and self.output_tracker.rates is None:
            raise Fault('output_encoder_missing_after_two_cycle_warmup')
        commands=super().__call__(attitude,speeds,plan)
        self.output_active_calls+=1
        return commands

    def observe_pair(self,sample):
        for mid,sign in ((0,1),(1,-1)):
            wheel=sample['wheels'][mid]
            if wheel['command_protocol_nm']!=sign*wheel['command_forward_nm']:
                raise Fault('output_encoder_calibrated_wheel_sign_mismatch')
        self.output_tracker.observe({m:w['feedback'] for m,w in sample['wheels'].items()},
                                    {0:1,1:-1})
        sample['attitude']['output_encoder_feedback']=dict(
            relative_forward_position_rad=self.output_tracker.position.copy(),
            difference_rate_rad_s=self.output_tracker.rates.copy() if self.output_tracker.rates else None,
            received_times=self.output_tracker.times.copy())
        super().observe_pair(sample)

    def extra_telemetry(self,sample):
        radius=self.source_plan['nominal_wheel_radius_m']
        return dict(output_encoder_common_offset_m=radius*sum(self.output_tracker.position.values())/2,
                    output_encoder_per_wheel_offset_m={m:radius*p for m,p in self.output_tracker.position.items()},
                    output_encoder_ready=self.output_tracker.rates is not None)
