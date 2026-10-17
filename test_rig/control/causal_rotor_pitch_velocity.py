"""Offline candidate: same-window causal rotor-angle plus body-pitch secant.

No device, packet or controller imports. Not connected to live control.
Uses already forward-signed continuous rotor/gear position, NOT noisy
independent absolute output-angle differences. Host timestamps are not
internal acquisition times; this is still nominal no-slip kinematics.
"""
from collections import deque
import math


class CausalRotorPitchVelocity:
    def __init__(self,radius_m=.04,window_s=.02,max_feedback_age_s=.015,max_gap_s=.025):
        if not all(math.isfinite(v) for v in (radius_m,window_s,max_feedback_age_s,max_gap_s)):
            raise ValueError('nonfinite_configuration')
        if not 0<radius_m<=.1 or not .02<=window_s<=.05 or not 0<max_feedback_age_s<=max_gap_s<=.025:
            raise ValueError('configuration_outside_candidate')
        self.radius,self.window,self.max_age,self.max_gap=radius_m,window_s,max_feedback_age_s,max_gap_s
        self.previous=None;self.history={m:deque() for m in (0,1)};self.ever_ready=False

    def update(self,t,pitch_deg,positions,received_times,reported_speeds):
        if any(set(x)!={0,1} for x in (positions,received_times,reported_speeds)):
            raise ValueError('both_wheel_samples_required')
        if not all(math.isfinite(v) for v in (t,pitch_deg,*positions.values(),*received_times.values(),*reported_speeds.values())):
            raise ValueError('nonfinite_sample')
        if any(not 0<=t-v<=self.max_age for v in received_times.values()):
            raise ValueError('stale_or_future_wheel_sample')
        raw=self.radius*sum(reported_speeds.values())/2
        theta=math.radians(pitch_deg)
        if self.previous is None:
            self.previous=(t,theta)
            return dict(ready=False,raw_proxy_m_s=raw,corrected_proxy_m_s=None,
                        reason='need_bracketing_body_angles')
        before,angle=self.previous
        if not .001<=t-before<=self.max_gap:raise ValueError('imu_sample_gap')
        if any(v<before for v in received_times.values()):
            raise ValueError('wheel_sample_before_imu_bracket')
        results={}
        for mid in (0,1):
            rt=received_times[mid];h=self.history[mid]
            if h and not .001<=rt-h[-1][0]<=self.max_gap:
                raise ValueError('wheel_sample_gap_or_order')
            aligned=angle+(theta-angle)*(rt-before)/(t-before)
            h.append((rt,positions[mid],aligned));start=rt-self.window
            while len(h)>2 and h[1][0]<=start:h.popleft()
            if h[0][0]>start+1e-12:continue
            x,y=h[0],h[1];weight=(start-x[0])/(y[0]-x[0])
            old_position=x[1]+weight*(y[1]-x[1]);old_pitch=x[2]+weight*(y[2]-x[2])
            relative=(positions[mid]-old_position)/self.window
            body=(aligned-old_pitch)/self.window
            results[mid]=dict(relative_rad_s=relative,body_rad_s=body,
                              corrected_m_s=self.radius*(relative+body),
                              window_start_host_t=start,window_end_host_t=rt)
        self.previous=(t,theta)
        if len(results)!=2:
            if self.ever_ready:raise ValueError('lost_velocity_window')
            return dict(ready=False,raw_proxy_m_s=raw,corrected_proxy_m_s=None,
                        reason='need_complete_causal_window')
        self.ever_ready=True
        return dict(ready=True,raw_proxy_m_s=raw,
                    corrected_proxy_m_s=sum(q['corrected_m_s'] for q in results.values())/2,
                    per_wheel=results,window_s=self.window,
                    internal_sensor_latency_calibrated=False,
                    scope='causal_same_window_nominal_kinematics_not_measured_floor_speed')
