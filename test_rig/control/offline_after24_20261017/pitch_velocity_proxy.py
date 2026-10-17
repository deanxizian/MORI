"""Offline kinematic study only. No motor, IMU, network or file I/O.

Forward wheel rotation and forward body pitch use the same angular sign.
For an axle-mounted encoder: wheel_absolute_rate = shaft_relative_rate +
body_pitch_rate. Multiplying by nominal tyre radius still assumes rolling
without slip. This is NOT ArduPilot EKF/AHRS, a floor measurement, or a
validated controller input. Sensor sampling delays inside the motor/IMU
remain unknown; host receive-time interpolation cannot remove those delays.
"""
import math


class PitchVelocityProxy:
    def __init__(self,radius_m=.04,max_feedback_age_s=.015,max_gap_s=.025):
        if not all(math.isfinite(v) for v in (radius_m,max_feedback_age_s,max_gap_s)):
            raise ValueError('nonfinite_configuration')
        if not 0<radius_m<=.1 or not 0<max_feedback_age_s<=max_gap_s<=.025:
            raise ValueError('configuration_outside_study')
        self.radius=radius_m
        self.max_age=max_feedback_age_s
        self.max_gap=max_gap_s
        self.previous=None

    def update(self,t,pitch_rate_dps,speeds,received_times):
        if set(speeds)!={0,1} or set(received_times)!={0,1}:
            raise ValueError('both_wheel_samples_required')
        if not all(math.isfinite(v) for v in (t,pitch_rate_dps,*speeds.values(),*received_times.values())):
            raise ValueError('nonfinite_sample')
        ages={m:t-received_times[m] for m in (0,1)}
        if any(not 0<=age<=self.max_age for age in ages.values()):
            raise ValueError('stale_or_future_wheel_sample')
        rate=math.radians(pitch_rate_dps)
        raw=self.radius*(speeds[0]+speeds[1])/2
        if self.previous is None:
            self.previous=(t,rate)
            return dict(ready=False,raw_proxy_m_s=raw,corrected_proxy_m_s=None,
                        reason='need_bracketing_imu_samples')
        previous_t,previous_rate=self.previous
        if not .001<=t-previous_t<=self.max_gap:
            raise ValueError('imu_sample_gap')
        if any(received_times[m]<previous_t for m in (0,1)):
            raise ValueError('wheel_sample_before_imu_bracket')
        aligned={m:previous_rate+(rate-previous_rate)*(received_times[m]-previous_t)/(t-previous_t)
                 for m in (0,1)}
        component=self.radius*(aligned[0]+aligned[1])/2
        result=dict(ready=True,raw_proxy_m_s=raw,body_pitch_component_m_s=component,
                    corrected_proxy_m_s=raw+component,
                    feedback_age_s=ages,aligned_pitch_rate_rad_s=aligned,
                    scope='nominal_no_slip_kinematics_not_validated_floor_speed')
        self.previous=(t,rate)
        return result
