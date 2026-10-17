#!/usr/bin/env python3
"""One three-second restrained ground trial; zero hardware I/O by default.

Experimental attitude PD only. No speed/position target, autonomous driving,
integrator, friction feedforward, service, or automatic restart. The operator
must prevent a fall and keep immediate physical power-cut access.
"""
import math

from air_trial import main as trial_main
from attitude import Fault, finite, clip
from protocol import RATIO


GROUND_PLAN=dict(
    name='restrained_ground_attitude_pd_native_damping_v5',duration_s=3.,control_phase='ground_pd',
    kp_nm_per_rad=1.5,kd_nm_per_rad_s=.05,
    native_wheel_damping_nm_per_rad_s=.05,feedforward_torque_limit_nm=.08,
    predicted_net_torque_limit_nm=.08,
    arm_native_wheel_damping_nm_per_rad_s=.15,
    pitch_limit_deg=12.,roll_limit_deg=8.,pitch_rate_limit_dps=100.,
    wheel_speed_limit_rad_s=2.,temperature_limit_c=70,
    estimated_torque_limit_nm=.12,loop_gap_s=.025,
    imu_age_limit_s=.01,feedback_deadline_s=.008,
    arm_pitch_limit_deg=8.,arm_roll_limit_deg=5.,trigger_pitch_deg=2.,
    arm_rate_limit_dps=10.,arm_pitch_span_deg=2.5,arm_wheel_speed_limit_rad_s=.2,
    capture_start_reference=True,start_on_pose=True,
    prearm_pitch_limit_deg=12.,prearm_roll_limit_deg=8.,
    manual_prearm_motion_rad_s=.2,trigger_still_s=0.,
    zero_arm_speed_limit_rad_s=.2,zero_arm_displacement_limit_rad=.06,
    nominal_wheel_radius_m=.04,rolling_path_limit_m=.08,
    differential_rolling_limit_m=.03,
    status='EXPERIMENTAL_RESTRAINED_ONLY_NOT_VALIDATED_BALANCE_GAINS',
    wait_upright_message='WAIT_UPRIGHT: 两轮停止；轮子着地，大致扶正即可，正在记录半秒平均姿态。',
    wait_tilt_message='WAIT_TILT: 已记下当前姿态，两轮仍停止。请轻扶防倒，比刚才缓慢前倾一点（约 2–3 度）；触发后只运行 3 秒。',
    active_message='RESTRAINED_GROUND_ACTIVE: 3 秒补偿开始；不要继续主动前后摇，轻扶防倒并允许轮子小幅滚动。',
)


def ground_command(attitude,forward_wheel_speeds,plan=GROUND_PLAN):
    """Positive forward tilt/rate requests forward wheel torque on both sides.

    Gains are initial experimental choices, not a plant identification result.
    A modest native wheel damper prevents an already-moving wheel from taking
    the same sustained torque as a stuck wheel. This is an experimental
    adjustment to the observed asymmetric response, not a friction model.
    No second host velocity damper is added. The actual closed-loop dynamics
    still need physical validation; this is not a proof of ground stability.
    """
    pitch,rate,roll=(attitude[k] for k in ('pitch_deg','pitch_rate_dps','roll_deg'))
    finite(pitch,rate,roll,*forward_wheel_speeds.values())
    if abs(pitch)>plan['pitch_limit_deg'] or abs(roll)>plan['roll_limit_deg']:
        raise Fault('body_tilt_stop')
    if abs(rate)>plan['pitch_rate_limit_dps']:
        raise Fault('body_rotation_rate_stop')
    if any(abs(v)>plan['wheel_speed_limit_rad_s'] for v in forward_wheel_speeds.values()):
        raise Fault('wheel_speed_stop')
    # Only the target shifts to the operator-held pose. Absolute pitch/roll
    # fault limits above retain the calibrated reference and are not widened.
    error=attitude.get('pitch_error_deg',pitch);finite(error)
    value=clip(plan['kp_nm_per_rad']*math.radians(error)+
               plan['kd_nm_per_rad_s']*math.radians(rate),plan['feedforward_torque_limit_nm'])
    # Native output command is quantized FF - quantized Kd * live speed.
    # Reserve one FF LSB so packet truncation cannot exceed the predicted
    # envelope at the last observed speed. Delayed speed/firmware behavior
    # mean this remains a prediction, NOT an independent hardware torque cap.
    kd_step=RATIO**2/128000000
    native_kd=math.floor(plan['native_wheel_damping_nm_per_rad_s']/kd_step)*kd_step
    net_cap=plan['predicted_net_torque_limit_nm']-RATIO/256000
    commands={}
    for mid,speed in forward_wheel_speeds.items():
        damping=native_kd*speed
        low=max(-plan['feedforward_torque_limit_nm'],-net_cap+damping)
        high=min(plan['feedforward_torque_limit_nm'],net_cap+damping)
        if low>high:
            raise Fault('native_braking_envelope_unavailable')
        commands[mid]=max(low,min(high,value))
    return commands


class WheelTravel:
    """Rotor/gear-derived rolling equivalents; not measured floor distance.

    Accumulate absolute motion so reversing cannot reset the path budget.
    Nominal radius ignores tyre deformation, slip, gear compliance and pitch.
    This is a secondary software stop, not a certified workspace boundary.
    """
    def __init__(self,rows,signs,plan=GROUND_PLAN):
        self.plan=plan;self.signs=signs
        self.origins={m:rows[m]['position_rad'] for m in (0,1)}
        finite(*self.origins.values())
        self.previous=self.origins.copy()
        self.offset={0:0.,1:0.};self.path={0:0.,1:0.}

    def snapshot(self):
        return dict(rotor_derived_origin_rad=self.origins.copy(),
                    forward_offset_m=self.offset.copy(),cumulative_path_m=self.path.copy(),
                    differential_offset_m=self.offset[0]-self.offset[1])

    def update(self,mid,row):
        position=row['position_rad'];finite(position)
        radius=self.plan['nominal_wheel_radius_m']
        self.path[mid]+=abs(position-self.previous[mid])*radius
        self.offset[mid]=(position-self.origins[mid])*self.signs[mid]*radius
        self.previous[mid]=position
        if self.path[mid]>=self.plan['rolling_path_limit_m']:
            raise Fault('wheel_rolling_path_stop')
        if abs(self.offset[0]-self.offset[1])>=self.plan['differential_rolling_limit_m']:
            raise Fault('differential_wheel_travel_stop')


def main(argv=None):
    return trial_main(argv,plan=GROUND_PLAN,start_flag='--run-restrained-ground-trial',
                      controller=ground_command,travel_factory=WheelTravel,description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
