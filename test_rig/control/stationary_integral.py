# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental conditional integration, using the existing AP anti-windup.

P/D, filters, mode1 packets and every runtime guard continue normally. This
does not disable motors or suppress all feedback near upright. Sensor-only
stationarity is not proof of support-free standing or measured floor speed.
"""
import math
from attitude import Fault,finite
from live_tuning import LiveTuningController


class StationaryIntegralGate:
    # Explicit experimental comparison constants, not identified plant data.
    ENTER_WHEEL_RAD_S=.03
    EXIT_WHEEL_RAD_S=.06
    ENTER_RATE_DPS=.5
    EXIT_RATE_DPS=1.5
    ENTER_ERROR_DEG=.5
    EXIT_ERROR_DEG=.75
    DWELL_S=.10

    def __init__(self):
        self.since=None;self.limited=False;self.previous=None
        self.transitions=0

    def update(self,t,error_deg,rate_dps,speeds):
        if set(speeds)!={0,1}:raise Fault('stationary_integral_requires_both_wheels')
        finite(t,error_deg,rate_dps,*speeds.values())
        if self.previous is not None and not .001<=t-self.previous<=.025:
            raise Fault('stationary_integral_sample_gap')
        self.previous=t
        wheel=max(abs(v) for v in speeds.values())
        before=self.limited
        if self.limited:
            if (wheel>=self.EXIT_WHEEL_RAD_S or abs(rate_dps)>=self.EXIT_RATE_DPS
                    or abs(error_deg)>=self.EXIT_ERROR_DEG):
                self.limited=False;self.since=None
        else:
            eligible=(wheel<=self.ENTER_WHEEL_RAD_S and abs(rate_dps)<=self.ENTER_RATE_DPS
                      and abs(error_deg)<=self.ENTER_ERROR_DEG)
            if not eligible:self.since=None
            elif self.since is None:self.since=t
            elif t-self.since>=self.DWELL_S:self.limited=True
        if self.limited!=before:self.transitions+=1
        return self.limited


class StationaryIntegralLiveController(LiveTuningController):
    def reset(self):
        super().reset()
        self.integral_gate=StationaryIntegralGate()

    def pitch_integrator_limit(self,attitude,speeds,plan,target,actual):
        if plan.get('stationary_integral_guard') is not True:
            raise Fault('stationary_integral_opt_in_required')
        error=math.degrees(target-actual)
        limited=self.integral_gate.update(attitude['t'],error,attitude['pitch_rate_dps'],speeds)
        attitude['stationary_integrator']=dict(growth_limited=limited,
            error_deg=error,transitions=self.integral_gate.transitions,
            scope='Existing AP motor-limit integration rule: block same-direction growth, allow unwinding; P/D and actuator guards remain active.')
        return limited

    def extra_telemetry(self,sample):
        info=sample['attitude']['stationary_integrator']
        return dict(stationary_integral_growth_limited=info['growth_limited'],
                    stationary_integral_transitions=info['transitions'])
