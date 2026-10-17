# SPDX-License-Identifier: GPL-3.0-or-later
"""Hardware-free port of the Rover-4.7.2 Balance Bot PID path.

Derived from ArduPilot AC_PID::update_all/update_i and
AR_AttitudeControl::get_throttle_out_from_pitch, commit
fb773567896014da007bca58358704d4a0d8516f. Upstream files and COPYING.txt
are preserved in reference_sources/ardupilot_rover_4_7_2.

Supported configuration: target/error/D low-pass filters, P/I/D/FF/DFF,
integrator limiting, current-pitch feedforward, adaptive target pitch limits.
The optional slew modifier is ported separately; notches and PD-sum limiter
remain disabled. An explicit MORI minimum modifier is distinct from upstream.
This is a documented Python port, NOT a running ArduPilot firmware instance.
The caller owns sensor health, timestamps, output scaling and all motor I/O.
"""
import math
from ardupilot_slew import SlewLimiter


def alpha(dt, hz):
    # AP_Math::calc_lowpass_alpha_dt for valid non-negative inputs.
    return 1. if hz == 0 else dt / (dt + 1. / (math.tau * hz))


def constrain(value, low, high):
    return max(low, min(high, value))


class BalancePitchPID:
    """ArduPilot convention: positive pitch leans backwards, output forwards.

    Output remains unbounded here, as in the inspected upstream method;
    upstream motor code and our adapter perform their respective saturation.
    Invalid input raises instead of silently returning zero as upstream PID
    does. This enables the MORI runner to stop both motors on an input fault.
    """
    def __init__(self, *, kp, ki, kd, imax, fltt=0., flte=0., fltd=10.,
                 ff=0., dff=0., pitch_ff=0.4, pitch_max=math.radians(5.),
                 limit_tc=.5, limit_threshold=.6,smax=0.,slew_tau=1.,slew_min_modifier=0.):
        values=(kp,ki,kd,imax,fltt,flte,fltd,ff,dff,pitch_ff,pitch_max,
                limit_tc,limit_threshold,smax,slew_tau,slew_min_modifier)
        if (not all(math.isfinite(v) and v >= 0 for v in values) or pitch_max <= 0
                or slew_tau<=0 or slew_min_modifier>1):
            raise ValueError('invalid_ardupilot_pid_parameters')
        self.kp,self.ki,self.kd,self.imax=kp,ki,kd,imax
        self.fltt,self.flte,self.fltd=fltt,flte,fltd
        self.ff,self.dff,self.pitch_ff=ff,dff,pitch_ff
        self.pitch_max,self.limit_tc,self.limit_threshold=pitch_max,limit_tc,limit_threshold
        self.smax,self.slew_tau,self.slew_min_modifier=smax,slew_tau,slew_min_modifier
        self.reset()

    def reset(self):
        self.target=self.error=self.derivative=self.target_derivative=self.integrator=0.
        self.low,self.high=-self.pitch_max,self.pitch_max
        self.first=True
        self.info={}
        self.slew=SlewLimiter(self.smax,self.slew_tau) if self.smax>0 else None

    def update(self, desired_pitch, actual_pitch, dt, motor_limit=False,*,now_ms=None):
        if not all(math.isfinite(v) for v in (desired_pitch,actual_pitch,dt)) or not 0 < dt <= 1:
            raise ValueError('invalid_ardupilot_pid_sample')
        limiting=self.limit_tc >= .01 and self.limit_threshold > 0
        target=constrain(desired_pitch,self.low,self.high) if limiting else desired_pitch
        pitch_limited=limiting and (target <= self.low or target >= self.high)
        reset=self.first
        if self.first:
            self.first=False
            self.target=target
            self.error=target-actual_pitch
            self.derivative=self.target_derivative=0.
        else:
            last_target,last_error=self.target,self.error
            self.target+=alpha(dt,self.fltt)*(target-self.target)
            self.error+=alpha(dt,self.flte)*(self.target-actual_pitch-self.error)
            self.derivative+=alpha(dt,self.fltd)*((self.error-last_error)/dt-self.derivative)
            self.target_derivative=(self.target-last_target)/dt
        if self.ki != 0:
            if not motor_limit or self.integrator*self.error < 0:
                self.integrator=constrain(self.integrator+self.error*self.ki*dt,
                                          -self.imax,self.imax)
        else:
            self.integrator=0.
        p,d=self.error*self.kp,self.derivative*self.kd
        slew_info={}
        if self.slew is not None:
            # Upstream monitors the PREVIOUS already-modified P+D output.
            raw_modifier=self.slew.modifier(self.info.get('p',0.)+self.info.get('d',0.),dt,now_ms)
            modifier=max(self.slew_min_modifier,raw_modifier)
            p*=modifier;d*=modifier
            slew_info=dict(pd_slew_raw_modifier=raw_modifier,pd_slew_modifier=modifier,
                           pd_slew_rate_output_per_s=self.slew.output_slew)
        ff=self.target*self.ff+self.target_derivative*self.dff
        pitch_ff=math.sin(actual_pitch)*self.pitch_ff
        output=p+d+self.integrator+ff+pitch_ff
        if limiting:
            increment=dt*self.pitch_max/self.limit_tc
            self.high=(max(self.high-increment,0.) if output <= -self.limit_threshold
                       else min(self.high+increment*.5,self.pitch_max))
            self.low=(min(self.low+increment,0.) if output >= self.limit_threshold
                      else max(self.low-increment*.5,-self.pitch_max))
        self.info=dict(target_rad=self.target,actual_rad=actual_pitch,error_rad=self.error,
                       p=p,i=self.integrator,d=d,ff=ff,pitch_ff=pitch_ff,raw_output=output,
                       motor_limit=bool(motor_limit),filter_reset=reset,
                       pitch_limited=pitch_limited,pitch_low_rad=self.low,pitch_high_rad=self.high)
        self.info.update(slew_info)
        if not all(math.isfinite(v) for v in (output,self.integrator,self.low,self.high)):
            raise ValueError('nonfinite_ardupilot_pid_state')
        return output
