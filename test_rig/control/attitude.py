"""Body-pitch estimation and bounded experimental attitude PD, without I/O.

Gains below are explicit initial experimental settings, not identified plant
parameters, and do not establish that the assembled robot can balance.
"""
import math
from calibration import angles, dot, norm, cross


class Fault(RuntimeError):
    pass


def finite(*values):
    if not all(math.isfinite(v) for v in values):
        raise Fault('nonfinite_control_value')


def clip(value,limit):
    return max(-limit,min(limit,value))


def validate_calibration(cal):
    vectors=[cal[k] for k in ('up_axis_raw','forward_gravity_axis_raw','positive_pitch_gyro_axis_raw')]
    for v in vectors:
        if len(v)!=3:
            raise Fault('invalid_axis_length')
        finite(*v)
        if abs(norm(v)-1)>1e-5:
            raise Fault('axis_not_normalized')
    u,d,p=vectors
    if any(abs(dot(a,b))>1e-5 for a,b in ((u,d),(u,p),(d,p))):
        raise Fault('axes_not_orthogonal')
    if norm([a-b for a,b in zip(cross(d,u),p)])>1e-5:
        raise Fault('gyro_gravity_axes_disagree')
    bias=cal['gyro_bias_dps']
    if len(bias)!=3:
        raise Fault('invalid_bias_length')
    finite(*bias)
    if norm(bias)>2:
        raise Fault('invalid_bias')
    if cal.get('gyro_sign_dynamic_check')!='PASS':
        raise Fault('dynamic_axis_check_required')
    signs=cal.get('wheel_signs')
    if not isinstance(signs,dict) or set(signs)!={'0','1'} or any(type(v) is not int or v not in (-1,1) for v in signs.values()):
        raise Fault('onsite_wheel_signs_required')


class PitchEstimator:
    def __init__(self,cal,*,fuse_roll=False):
        validate_calibration(cal)
        self.cal=cal
        self.previous=None
        self.pitch=None
        self.roll=None
        self.fuse_roll=fuse_roll
        self.dynamic_outside_normal_since=None
        self.rotating_low_g_since=None
        self.last_fast_pitch_rotation=None

    def update(self,sample,*,dynamic=False,allow_rotating_low_g=False,rotating_low_g_history_s=0.):
        finite(sample['t_read_complete'],*sample['accel_g'],*sample['gyro_dps'])
        a=angles(sample,self.cal)
        a_norm=norm(sample['accel_g'])
        timestamp=sample['t_read_complete']
        finite(rotating_low_g_history_s)
        if not 0.<=rotating_low_g_history_s<=.02:raise Fault('invalid_rotating_low_g_history')
        if dynamic:
            # A finite rising maneuver can contain brief translational or
            # rotational acceleration. Never use those frames as gravity.
            # Keep an immediate large-impact/freefall guard and reject a
            # sustained departure from the original test window.
            fast=abs(a['pitch_rate_dps'])>=100.
            if allow_rotating_low_g and fast:self.last_fast_pitch_rotation=timestamp
            recent=(rotating_low_g_history_s>0. and self.last_fast_pitch_rotation is not None
                    and 0.<=timestamp-self.last_fast_pitch_rotation<rotating_low_g_history_s)
            rotating_low_g=(allow_rotating_low_g and .05<a_norm<=.2 and (fast or recent))
            if not (.2<a_norm<3. or rotating_low_g):
                raise Fault('acceleration_outside_dynamic_window')
            # An off-axis accelerometer can briefly approach zero specific
            # force during rapid rotation without being invalid. Opt-in is
            # limited to 20 ms and gyro-only estimation. The optional <=20 ms
            # history covers deceleration through a turning point; static low-g
            # without preceding fast rotation still rejects immediately.
            if rotating_low_g:
                if self.rotating_low_g_since is None:self.rotating_low_g_since=timestamp
                elif timestamp-self.rotating_low_g_since>=.02:
                    raise Fault('sustained_rotating_low_g')
            else:self.rotating_low_g_since=None
            if not .5<a_norm<1.5:
                if self.dynamic_outside_normal_since is None:
                    self.dynamic_outside_normal_since=timestamp
                elif timestamp-self.dynamic_outside_normal_since>=.05:
                    raise Fault('sustained_dynamic_acceleration')
            else:
                self.dynamic_outside_normal_since=None
        else:
            self.dynamic_outside_normal_since=None
            self.rotating_low_g_since=None
            self.last_fast_pitch_rotation=None
            if not .5<a_norm<1.5:
                raise Fault('acceleration_outside_test_window')
        roll_accel=math.degrees(math.asin(clip(dot(sample['accel_g'],self.cal['positive_pitch_gyro_axis_raw'])/a_norm,1)))
        dt=timestamp-self.previous if self.previous is not None else .01
        if not .001<=dt<=.025:
            raise Fault('imu_sample_gap')
        weight=dt/(.5+dt) if not dynamic and abs(a_norm-1)<.12 else 0
        if dynamic and self.pitch is None:
            raise Fault('dynamic_estimator_requires_static_initialization')
        gyro=[sample['gyro_dps'][i]-self.cal['gyro_bias_dps'][i] for i in range(3)]
        pitch_before=math.radians(self.pitch if self.pitch is not None else a['pitch_accel_deg'])
        # roll here is the signed lateral gravity angle, not Euler roll about
        # a fixed sensor axis. With g = cos(r)*sin(p)*d + sin(r)*axis +
        # cos(r)*cos(p)*up and dg/dt = -omega x g, its rate is
        # omega_up*sin(p) - omega_d*cos(p). This remains defined at pitch 90.
        roll_rate=(dot(gyro,self.cal['up_axis_raw'])*math.sin(pitch_before)-
                   dot(gyro,self.cal['forward_gravity_axis_raw'])*math.cos(pitch_before))
        if self.roll is None or not self.fuse_roll:
            self.roll=roll_accel
        else:
            roll_predicted=self.roll+roll_rate*dt
            self.roll=roll_predicted+weight*(roll_accel-roll_predicted)
        if self.pitch is None:
            self.pitch=a['pitch_accel_deg']
        else:
            predicted=self.pitch+a['pitch_rate_dps']*dt
            error=(a['pitch_accel_deg']-predicted+180)%360-180
            # Gyro follows fast rotation; gravity corrects slow drift only.
            # Reduce the acceleration correction during non-gravity motion.
            self.pitch=predicted+weight*error
        self.previous=timestamp
        return dict(t=timestamp,dt=dt,pitch_deg=self.pitch,roll_deg=self.roll,
                    pitch_rate_dps=a['pitch_rate_dps'],accel_norm_g=a_norm,
                    pitch_accel_deg=a['pitch_accel_deg'],roll_accel_deg=roll_accel,
                    roll_rate_dps=roll_rate,roll_fused=self.fuse_roll,
                    dynamic_acceleration_window=dynamic,gravity_correction_weight=weight,
                    rotating_low_g_transient=bool(dynamic and self.rotating_low_g_since is not None),
                    rotating_low_g_recent_context=bool(dynamic and rotating_low_g_history_s>0.
                        and self.rotating_low_g_since is not None and abs(a['pitch_rate_dps'])<100.))


AIR_PLAN=dict(name='suspended_attitude_breakaway_adjusted_v3',duration_s=10.,
              kp_nm_per_rad=1.0,kd_nm_per_rad_s=.015,
              native_wheel_damping_nm_per_rad_s=.15,feedforward_torque_limit_nm=.08,
              predicted_net_torque_limit_nm=.08,
              pitch_limit_deg=25.,roll_limit_deg=20.,pitch_rate_limit_dps=100.,
              wheel_speed_limit_rad_s=1.5,temperature_limit_c=70,
              estimated_torque_limit_nm=.12,loop_gap_s=.025,
              imu_age_limit_s=.01,feedback_deadline_s=.008,
              arm_pitch_limit_deg=5.,arm_roll_limit_deg=5.,
              status='EXPERIMENTAL_AIR_ONLY_NOT_BALANCE_GAINS')


def air_command(attitude,forward_wheel_speeds,plan=AIR_PLAN):
    """Body PD feedforward. Wheel damping executes inside each servo.

    The host uses wheel speed for fault checking and a braking envelope only;
    it must not duplicate the native velocity damper as another control term.
    These remain suspended sign-check settings, not released ground gains.
    """
    pitch,rate,roll=(attitude[k] for k in ('pitch_deg','pitch_rate_dps','roll_deg'))
    finite(pitch,rate,roll,*forward_wheel_speeds.values())
    if abs(pitch)>plan['pitch_limit_deg'] or abs(roll)>plan['roll_limit_deg']:
        raise Fault('body_tilt_stop')
    if abs(rate)>plan['pitch_rate_limit_dps']:
        raise Fault('body_rotation_rate_stop')
    if any(abs(v)>plan['wheel_speed_limit_rad_s'] for v in forward_wheel_speeds.values()):
        raise Fault('wheel_speed_stop')
    base=plan['kp_nm_per_rad']*math.radians(pitch)+plan['kd_nm_per_rad_s']*math.radians(rate)
    commands={}
    for mid,speed in forward_wheel_speeds.items():
        value=clip(base,plan['feedforward_torque_limit_nm'])
        # Native torque = FF - Kd * speed. Bound predicted net torque during
        # reversal, without inserting a second host speed-control loop.
        # This uses delayed feedback and is NOT an independent hardware clamp.
        damping=plan['native_wheel_damping_nm_per_rad_s']*speed
        cap=plan['predicted_net_torque_limit_nm']
        low=max(-plan['feedforward_torque_limit_nm'],-cap+damping)
        high=min(plan['feedforward_torque_limit_nm'],cap+damping)
        if low>high:
            raise Fault('native_braking_envelope_unavailable')
        commands[mid]=max(low,min(high,value))
    return commands
