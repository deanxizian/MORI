#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""One finite first-layer self-righting trial; no I/O by default.

Experimental large-angle PD -> blended capture -> ArduPilot pitch PID with
limited zero-speed target and differential correction. This is an S288 adapter,
not upstream ArduPilot firmware or a proven self-righting controller. Geometry
screening and synthetic traces do not identify the real plant. First run keeps
the existing 0.12 Nm, 4 rad/s, 70 C and travel limits. No fault retry/re-arm.
"""
import math

from air_trial import main as trial_main
from ardupilot_balance_core import BalancePitchPID
from attitude import Fault,clip,finite
from ground_ardupilot_rate_window import RATE_PLAN
from ground_hold_trial import HoldTravel
from ground_trial import ground_command
from protocol import RATIO
from velocity_envelope import velocity_targets


SELF_RIGHT_PLAN=dict(
    RATE_PLAN,name='first_layer_single_self_righting_v18_lower_wheel_damping',duration_s=10.,
    motion_hold_reason='retired_self_righting_profiles_after_trial31_post_stop_flip; review stopping behavior before a new rising profile',
    control_phase='self_righting',capture_start_reference=False,start_on_pose=True,
    include_wheel_position_feedback=True,
    fuse_roll=True,
    native_wheel_damping_nm_per_rad_s=.010,
    pitch_limit_deg=100.,arm_pitch_min_deg=75.,arm_pitch_limit_deg=100.,
    arm_rate_limit_dps=3.,arm_pitch_span_deg=1.5,arm_wheel_speed_limit_rad_s=.1,
    prearm_countdown_s=3.,
    rise_kp_nm_per_rad=.18,rise_kd_nm_per_rad_s=.06,
    rise_ramp_s=.30,rise_timeout_s=3.5,rise_progress_time_s=1.5,
    rise_min_progress_deg=3.,rise_wrong_way_deg=5.,
    capture_pitch_deg=8.,capture_rate_dps=35.,capture_velocity_m_s=.12,
    capture_blend_s=.6,captured_pitch_limit_deg=25.,
    speed_target_gain_deg_per_m_s=15.,speed_target_limit_deg=2.5,
    speed_filter_tau_s=.08,speed_target_slew_dps=10.,
    differential_kp_nm_per_rad=.025,differential_kd_nm_per_rad_s=.01,
    differential_limit_nm=.025,
    stable_pitch_deg=3.,stable_rate_dps=10.,stable_velocity_m_s=.03,
    stable_differential_speed_rad_s=.2,stable_duration_s=2.,
    status='EXPERIMENTAL_FIRST_SELF_RIGHTING_NOT_PHYSICALLY_VALIDATED',
    wait_upright_message='WAIT_LYING: 两轮停止；等待车身约 75–100 度躺倒并静止半秒。',
    pose_ready_message='LYING_READY: 已识别躺向，3 秒后开始一次有限起身。请留意并准备接住。',
    active_message='SELF_RIGHTING_ACTIVE: 现在开始单次起身，最多 10 秒；前 3.5 秒未进入接管区即停止，到时或保护触发也停止，不自动重试。',
)


def rolling_speed(attitude,speeds,plan):
    """Pure-roll velocity estimate, including body-relative encoder kinematics.

    Unified positive wheel rotation and positive pitch both rotate about -X.
    Wheel rotation in the world = wheel relative to body + body pitch. Slip,
    loaded radius and lateral motion remain unmeasured.
    """
    if set(speeds)!={0,1}:
        raise Fault('self_righting_requires_both_wheels')
    finite(*speeds.values(),attitude['pitch_rate_dps'])
    return plan['nominal_wheel_radius_m']*(
        .5*(speeds[0]+speeds[1])+math.radians(attitude['pitch_rate_dps']))


def position_rates(a,speeds,previous_positions,previous_times,dt,plan):
    """Encoder differences use their own host receive boundary when opted in.

    Host reception is not the servo's internal sample clock. The serial
    deadline bounds that uncertainty; never divide encoder deltas by IMU dt.
    """
    positions=a['wheel_position_forward_rad']
    if not plan.get('use_wheel_feedback_timestamps',False):
        return ({m:(positions[m]-previous_positions[m])/dt for m in (0,1)}
                if previous_positions is not None else speeds.copy()),None
    times=a.get('wheel_feedback_received_monotonic')
    if not isinstance(times,dict) or set(times)!={0,1}:raise Fault('wheel_feedback_timestamp_required')
    for mid in (0,1):
        finite(times[mid],a['t'])
        if not 0.<=a['t']-times[mid]<=plan['loop_gap_s']:
            raise Fault('stale_or_future_wheel_feedback')
    if previous_positions is None:return speeds.copy(),times.copy()
    if previous_times is None:raise Fault('previous_wheel_feedback_timestamp_required')
    rates={}
    for mid in (0,1):
        gap=times[mid]-previous_times[mid]
        if not .001<=gap<=plan['loop_gap_s']:raise Fault('wheel_feedback_time_gap')
        rates[mid]=(positions[mid]-previous_positions[mid])/gap
    return rates,times.copy()


def budget(requests,speeds,plan,compensation=0.):
    """Retain the existing quantization-aware FF + native Kd envelope."""
    kd_step=RATIO**2/128000000
    kd=math.floor(plan['native_wheel_damping_nm_per_rad_s']/kd_step)*kd_step
    finite(compensation)
    if not 0.<=compensation<=1.:
        raise Fault('invalid_damping_compensation')
    cap=plan['predicted_net_torque_limit_nm']-RATIO/256000
    commands={}
    for mid,speed in speeds.items():
        finite(requests[mid],speed)
        low=max(-plan['feedforward_torque_limit_nm'],-cap+kd*speed)
        high=min(plan['feedforward_torque_limit_nm'],cap+kd*speed)
        if low>high:
            raise Fault('native_braking_envelope_unavailable')
        requested_ff=requests[mid]+compensation*kd*speed
        commands[mid]=max(low,min(high,requested_ff))
    return commands


def govern_rise_speed(requests,speeds,plan,mix,position_speeds=None):
    """Continuous net-torque envelope before the independent overspeed stop.

    The optional governor reduces acceleration approaching either speed target
    and requests braking beyond it. It fades out during capture; balancing
    retains its own velocity/attitude controller. Encoder speed is not ground
    speed and this is not traction control.
    """
    if 'rise_speed_target_rad_s' not in plan:
        return requests.copy()
    target=plan['rise_speed_target_rad_s'];gain=plan['rise_speed_gain_nm_per_rad_s']
    finite(target,gain,mix)
    if not (0.<target<plan['wheel_speed_limit_rad_s'] and gain>0. and 0.<=mix<=1.):
        raise Fault('invalid_rise_speed_governor')
    out={}
    for mid,speed in speeds.items():
        finite(speed,requests[mid])
        estimates=[speed]
        if position_speeds is not None:
            finite(position_speeds[mid])
            estimates.append(position_speeds[mid])
        # Rotor-position differences provide a separate short-window rate.
        # Intersect both envelopes rather than trusting a lagging filtered
        # speed during acceleration or abruptly changing signs on reversal.
        lower=max(-gain*(target+s) for s in estimates)
        upper=min(gain*(target-s) for s in estimates)
        if lower>upper:
            raise Fault('inconsistent_velocity_estimates')
        governed=max(lower,min(upper,requests[mid]))
        out[mid]=requests[mid]+(1.-mix)*(governed-requests[mid])
    return out


def rise_damping(pitch_deg,plan):
    """Angle-scheduled body damping; does not change wheel-loop gains or caps."""
    if 'rise_far_kd_nm_per_rad_s' not in plan:
        return plan['rise_kd_nm_per_rad_s']
    far=plan['rise_far_kd_nm_per_rad_s'];near=plan['rise_near_kd_nm_per_rad_s']
    lo=plan['rise_damping_near_pitch_deg'];hi=plan['rise_damping_far_pitch_deg']
    finite(pitch_deg,far,near,lo,hi)
    if not (0.<far<=near<=.2 and 0.<lo<hi<plan['pitch_limit_deg']):
        raise Fault('invalid_rise_damping_profile')
    mix=max(0.,min(1.,(abs(pitch_deg)-lo)/(hi-lo)))
    return near+(far-near)*mix


def recovery_signal(theta,rate,plan):
    """Optional bounded body-rate reference; default preserves the old PD.

    The feedforward and gains are experimental, not identified shaft torque.
    A rate reference is a soft control target, never a replacement for the
    independent body-rate stop. Its near-zero slope can match the balance PID.
    """
    if 'recovery_rate_max_dps' not in plan:
        kd=rise_damping(theta,plan)
        return plan['rise_kp_nm_per_rad']*math.radians(theta)+kd*math.radians(rate),kd,None
    maximum,tau,kd,gravity=(plan[k] for k in ('recovery_rate_max_dps','recovery_settle_time_s',
        'recovery_rate_gain_nm_per_rad_s','recovery_gravity_ff_nm'))
    finite(theta,rate,maximum,tau,kd,gravity)
    if not (0.<maximum<plan['rise_pitch_rate_limit_dps'] and .08<=tau<=.5 and
            0.<kd<=.2 and 0.<=gravity<=plan['control_torque_limit_nm']):
        raise Fault('invalid_recovery_rate_reference')
    if 'recovery_mid_gravity_ff_nm' in plan:
        mid,inner,near,far,outer=(plan[k] for k in ('recovery_mid_gravity_ff_nm',
            'recovery_mid_inner_deg','recovery_mid_full_near_deg',
            'recovery_mid_full_far_deg','recovery_mid_outer_deg'))
        finite(mid,inner,near,far,outer)
        if not (gravity<=mid<=plan['control_torque_limit_nm'] and
                0.<inner<near<far<outer<plan['arm_pitch_min_deg']):
            raise Fault('invalid_mid_recovery_feedforward')
        x=abs(theta)
        enter=max(0.,min(1.,(outer-x)/(outer-far)))
        leave=max(0.,min(1.,(x-inner)/(near-inner)))
        mix=min(enter*enter*(3.-2.*enter),leave*leave*(3.-2.*leave))
        gravity+=(mid-gravity)*mix
    desired=-clip(math.radians(theta)/tau,math.radians(maximum))
    value=gravity*math.sin(math.radians(theta))+kd*(math.radians(rate)-desired)
    return value,kd,math.degrees(desired)


class SelfRightingController:
    def __init__(self):
        self.reset()

    def reset(self):
        self.phase='READY'
        self.fault=None
        self.begin=self.previous=self.capture_begin=None
        self.start_pitch=None
        self.best_progress=0.
        self.pid=None
        self.velocity=0.
        self.pitch_target=0.
        self.previous_limited=False
        self.origins=None
        self.events=[]
        self.stable_since=None
        self.stable_s=self.max_stable_s=0.
        self.config=None
        self.applied_damping=None
        self.gyro_pitch=None
        self.rise_begin=None
        self.rise_initial_common=0.
        self.previous_net_common=0.
        self.pre_roll_exit=None
        self.previous_positions=None
        self.previous_feedback_times=None
        self.velocity_targets=None
        self.previous_velocity_targets={0:0.,1:0.}

    def validate_arm(self,a,speeds,plan):
        # Guard-only path: never initialize a rising phase or integrate PID
        # while the runner still sends zero feedforward.
        ground_command(a,speeds,plan)
        rolling_speed(a,speeds,plan)
        if plan.get('use_wheel_feedback_timestamps',False):
            position_rates(a,speeds,None,None,a['dt'],plan)
        rise_damping(a['pitch_deg'],plan)
        recovery_signal(a['pitch_deg'],a['pitch_rate_dps'],plan)
        rise_rate_limit=plan.get('rise_pitch_rate_limit_dps',plan['pitch_rate_limit_dps'])
        finite(rise_rate_limit)
        extension=plan.get('allow_inward_rate_extension',False)
        if type(extension) is not bool:raise Fault('invalid_inward_rate_extension')
        if extension and (not 0.<plan.get('rise_outward_pitch_rate_limit_dps',float('inf'))<=400.):
            raise Fault('outward_rate_guard_required')
        if not plan['pitch_rate_limit_dps']<=rise_rate_limit<=(500. if extension else 400.):
            raise Fault('invalid_rise_rate_limit')
        outward=plan.get('rise_outward_pitch_rate_limit_dps',rise_rate_limit)
        finite(outward)
        if not plan['pitch_rate_limit_dps']<=outward<=rise_rate_limit:raise Fault('invalid_outward_rate_limit')
        rise_speed_limit=plan.get('rise_wheel_speed_limit_rad_s',plan['wheel_speed_limit_rad_s'])
        finite(rise_speed_limit)
        speed_extension=plan.get('allow_wheel_speed_extension',False)
        if type(speed_extension) is not bool:
            raise Fault('invalid_wheel_speed_extension')
        # Explicit experimental opt-in only.16.5rad/s is the manufacturer's
        #12V no-load reference, not a qualified loaded/hardware limiter.
        speed_ceiling=16.5 if speed_extension else 15.5
        if not plan['wheel_speed_limit_rad_s']<=rise_speed_limit<=speed_ceiling:
            raise Fault('invalid_rise_wheel_speed_limit')
        rise_ff=plan.get('rise_feedforward_torque_limit_nm',plan['feedforward_torque_limit_nm'])
        finite(rise_ff)
        if not plan['feedforward_torque_limit_nm']<=rise_ff<=.60:
            raise Fault('invalid_rise_feedforward_limit')
        for key in ('native_wheel_damping_nm_per_rad_s','rise_native_wheel_damping_nm_per_rad_s',
                    'pre_roll_native_wheel_damping_nm_per_rad_s'):
            damping=plan.get(key,plan['native_wheel_damping_nm_per_rad_s'])
            finite(damping)
            if not 0.<damping<=.15:
                raise Fault('invalid_phase_native_damping')
        if type(plan.get('pre_roll_compensate_native_damping',False)) is not bool:
            raise Fault('invalid_pre_roll_compensation')
        if type(plan.get('rise_speed_position_guard',False)) is not bool:
            raise Fault('invalid_position_speed_guard')
        if type(plan.get('native_velocity_control',False)) is not bool:
            raise Fault('invalid_native_velocity_control')
        if plan.get('native_velocity_control'):
            velocity_targets({0:0.,1:0.},speeds,speeds,{0:0.,1:0.},a['dt'],plan)
        preload=plan.get('pre_roll_duration_s',0.)
        finite(preload)
        if preload:
            values=[plan[k] for k in ('pre_roll_ramp_s','pre_roll_torque_nm',
                'pre_roll_speed_limit_rad_s','pre_roll_travel_limit_m')]
            finite(*values)
            if not (0.<preload<=.5 and 0.<values[0]<=preload and
                    0.<values[1]<=plan['control_torque_limit_nm'] and
                    0.<values[2]<plan['wheel_speed_limit_rad_s'] and
                    0.<values[3]<=plan['net_rolling_limit_m']):
                raise Fault('invalid_pre_roll_plan')
            target=plan.get('pre_roll_target_rad_s',0.)
            finite(target)
            if type(plan.get('pre_roll_target_both_wheels',False)) is not bool:
                raise Fault('invalid_pre_roll_target_policy')
            if not 0.<=target<plan['pre_roll_speed_limit_rad_s']:
                raise Fault('invalid_pre_roll_target')
        if not (plan['arm_pitch_min_deg']<=abs(a['pitch_deg'])<=plan['arm_pitch_limit_deg']):
            raise Fault('self_righting_requires_lying_start')
        if (abs(a['roll_deg'])>plan['arm_roll_limit_deg'] or
                abs(a['pitch_rate_dps'])>plan['arm_rate_limit_dps'] or
                any(abs(v)>plan['arm_wheel_speed_limit_rad_s'] for v in speeds.values())):
            raise Fault('self_righting_start_not_still')

    def transition(self,phase,a):
        self.phase=phase
        self.events.append(dict(phase=phase,t=a['t'],pitch_deg=a['pitch_deg'],
                                pitch_rate_dps=a['pitch_rate_dps']))

    def __call__(self,a,speeds,plan=SELF_RIGHT_PLAN):
        if self.fault is not None:
            raise Fault('self_righting_fault_latched_'+self.fault)
        try:
            if self.start_pitch is not None and 'rise_outward_pitch_rate_limit_dps' in plan:
                direction=1. if self.start_pitch>0. else -1.
                if direction*a['pitch_rate_dps']>plan['rise_outward_pitch_rate_limit_dps']:
                    raise Fault('body_outward_rotation_rate_stop')
            return self.update(a,speeds,plan)
        except Exception as exc:
            self.fault=str(exc) or type(exc).__name__
            self.phase='FAULT'
            raise

    def update(self,a,speeds,plan):
        rate_limit=plan.get('rise_pitch_rate_limit_dps',plan['pitch_rate_limit_dps']) if self.phase=='RISING' else plan['pitch_rate_limit_dps']
        speed_limit=plan.get('rise_wheel_speed_limit_rad_s',plan['wheel_speed_limit_rad_s']) if self.phase=='RISING' else plan['wheel_speed_limit_rad_s']
        ground_command(a,speeds,dict(plan,pitch_rate_limit_dps=rate_limit,wheel_speed_limit_rad_s=speed_limit))
        v=rolling_speed(a,speeds,plan)
        positions=a.get('wheel_position_forward_rad',{})
        if set(positions)!={0,1}:
            raise Fault('self_righting_requires_wheel_positions')
        finite(a['t'],a['dt'],*positions.values())
        config=tuple(sorted(plan.items()))
        if self.config is not None and config!=self.config:
            raise Fault('self_righting_parameters_changed')
        self.config=config
        dt=a['dt'] if self.previous is None else a['t']-self.previous
        if not .001<=dt<=plan['loop_gap_s']:
            raise Fault('self_righting_sample_gap')
        self.previous=a['t']
        position_speeds,self.previous_feedback_times=position_rates(a,speeds,
            self.previous_positions,self.previous_feedback_times,dt,plan)
        self.previous_positions=positions.copy()
        if self.begin is None:
            self.validate_arm(a,speeds,plan)
            self.begin=a['t']
            self.start_pitch=a['pitch_deg']
            self.gyro_pitch=a['pitch_deg']
            self.origins=positions.copy()
            self.velocity=v
            if plan.get('pre_roll_duration_s',0.):
                self.transition('PRE_ROLL',a)
            else:
                self.rise_begin=a['t']
                self.transition('RISING',a)
        else:
            self.gyro_pitch+=a['pitch_rate_dps']*dt
        elapsed=a['t']-self.begin
        if elapsed>plan['duration_s']+plan['loop_gap_s']:
            raise Fault('self_righting_duration_exceeded')
        self.velocity+=dt/(plan['speed_filter_tau_s']+dt)*(v-self.velocity)
        theta,rate=a['pitch_deg'],a['pitch_rate_dps']
        polarity=plan.get('rise_polarity',1)
        if polarity not in (-1,1):raise Fault('invalid_rise_polarity')
        recovery,body_damping,desired_body_rate=recovery_signal(theta,rate,plan)
        recovery*=polarity
        direction=1. if self.start_pitch>0 else -1.
        progress=abs(self.start_pitch)-direction*theta
        if self.phase=='PRE_ROLL':
            if progress < -plan['rise_wrong_way_deg']:
                raise Fault('self_righting_wrong_way')
            if direction*theta < -plan['capture_pitch_deg']:
                raise Fault('self_righting_uncaptured_overshoot')
            if max(abs(s) for s in speeds.values())>plan['pre_roll_speed_limit_rad_s']:
                raise Fault('pre_roll_speed_stop')
            if max(abs(positions[m]-self.origins[m]) for m in (0,1))*plan['nominal_wheel_radius_m']>plan['pre_roll_travel_limit_m']:
                raise Fault('pre_roll_travel_stop')
            # Only one timed preparation. Genuine inward motion may end it
            # early; no return to preparation after capture or a fault.
            target=plan.get('pre_roll_target_rad_s',0.)
            toward=[-direction*polarity*s for s in speeds.values()]
            attained=min(toward) if plan.get('pre_roll_target_both_wheels',False) else max(toward)
            at_target=(target>0. and attained>=target)
            if elapsed>=plan['pre_roll_duration_s'] or progress>=5. or at_target:
                self.pre_roll_exit='inward_progress' if progress>=5. else 'speed_target' if at_target else 'time_limit'
                self.rise_begin=a['t']
                self.rise_initial_common=self.previous_net_common
                self.transition('RISING',a)
        rise_elapsed=a['t']-self.rise_begin if self.rise_begin is not None else 0.
        if self.phase=='RISING':
            self.best_progress=max(self.best_progress,progress)
            if progress < -plan['rise_wrong_way_deg']:
                raise Fault('self_righting_wrong_way')
            # Passing zero fast is not successful capture; do not permit
            # uncontrolled swinging to the opposite fallen posture.
            if direction*theta < -plan['capture_pitch_deg']:
                raise Fault('self_righting_uncaptured_overshoot')
            if rise_elapsed>=plan['rise_progress_time_s'] and self.best_progress<plan['rise_min_progress_deg']:
                raise Fault('self_righting_no_lift_progress')
            if (abs(theta)<=plan['capture_pitch_deg'] and abs(rate)<=plan['capture_rate_dps']
                    and abs(v)<=plan['capture_velocity_m_s']):
                self.capture_begin=a['t']
                self.transition('CAPTURE',a)
                self.pid=BalancePitchPID(
                    kp=plan['ap_kp'],ki=plan['ap_ki'],kd=plan['ap_kd'],imax=plan['ap_imax'],
                    fltt=plan['ap_fltt_hz'],flte=plan['ap_flte_hz'],fltd=plan['ap_fltd_hz'],
                    ff=plan['ap_ff'],dff=plan['ap_dff'],pitch_ff=plan['ap_pitch_ff'],
                    pitch_max=math.radians(plan['ap_pitch_max_deg']),
                    limit_tc=plan['ap_limit_tc_s'],limit_threshold=plan['ap_limit_threshold'])
            elif rise_elapsed>=plan['rise_timeout_s']:
                raise Fault('self_righting_capture_timeout')
        mix=0.
        if self.phase in ('CAPTURE','BALANCE'):
            if abs(theta)>plan['captured_pitch_limit_deg']:
                raise Fault('self_righting_capture_lost')
            desired=clip(-plan['speed_target_gain_deg_per_m_s']*self.velocity,
                         plan['speed_target_limit_deg'])
            self.pitch_target+=clip(desired-self.pitch_target,plan['speed_target_slew_dps']*dt)
            actual=-math.radians(theta)
            target=-math.radians(self.pitch_target)
            mix=min(1.,(a['t']-self.capture_begin)/plan['capture_blend_s'])
            # During blending, do not integrate a PID output not yet applied.
            output=self.pid.update(target,actual,dt,self.previous_limited or mix<1.)
            balance=plan['output_scale_nm']*output
            common=(1-mix)*recovery+mix*balance
            if mix>=1. and self.phase=='CAPTURE':
                self.transition('BALANCE',a)
        else:
            common=recovery
        ramp=min(1.,rise_elapsed/plan['rise_ramp_s'])
        # Cap BEFORE ramp; otherwise a saturated P term would bypass the ramp.
        cap=plan.get('control_torque_limit_nm',plan['feedforward_torque_limit_nm'])
        if self.phase=='PRE_ROLL':
            ramp=min(1.,elapsed/plan['pre_roll_ramp_s'])
            common=-direction*polarity*plan['pre_roll_torque_nm']*ramp
        else:
            common=(1.-ramp)*self.rise_initial_common+clip(common,cap)*ramp
        common_before_friction=common
        friction_ff=0.
        if plan.get('balance_friction_ff_nm',0.):
            amplitude=plan['balance_friction_ff_nm'];scale=plan['balance_friction_soft_nm']
            finite(amplitude,scale)
            if not 0.<amplitude<=.05 or not 0.<scale<=.05:raise Fault('invalid_balance_friction_adapter')
            friction_ff=amplitude*math.tanh(common/scale)*mix
            common+=friction_ff
        difference=(positions[0]-self.origins[0])-(positions[1]-self.origins[1])
        correction=clip(plan['differential_kp_nm_per_rad']*difference+
                        plan['differential_kd_nm_per_rad_s']*(speeds[0]-speeds[1]),
                        plan['differential_limit_nm'])*ramp
        ungoverned={0:common-correction,1:common+correction}
        requests=govern_rise_speed(ungoverned,speeds,plan,mix,
            position_speeds if plan.get('rise_speed_position_guard',False) else None)
        governor_limited=any(abs(requests[m]-ungoverned[m])>1e-12 for m in (0,1))
        compensation=(float(plan.get('pre_roll_compensate_native_damping',False))
            if self.phase=='PRE_ROLL' else
            (1.-mix) if plan.get('rise_compensate_native_damping',False) else 0.)
        baseline_damping=plan['native_wheel_damping_nm_per_rad_s']
        rising_damping=plan.get('rise_native_wheel_damping_nm_per_rad_s',baseline_damping)
        self.applied_damping=min(max(rising_damping,baseline_damping),
            max(min(rising_damping,baseline_damping),
                rising_damping+(baseline_damping-rising_damping)*mix))
        if self.phase=='PRE_ROLL':
            self.applied_damping=plan.get('pre_roll_native_wheel_damping_nm_per_rad_s',rising_damping)
        ff_limit=plan.get('rise_feedforward_torque_limit_nm',plan['feedforward_torque_limit_nm']) if self.phase=='RISING' else plan['feedforward_torque_limit_nm']
        command_plan=dict(plan,native_wheel_damping_nm_per_rad_s=self.applied_damping,
                          feedforward_torque_limit_nm=ff_limit)
        velocity_info=None
        if plan.get('native_velocity_control'):
            self.velocity_targets,velocity_info=velocity_targets(requests,speeds,position_speeds,
                self.previous_velocity_targets,dt,plan)
            self.previous_velocity_targets=self.velocity_targets.copy()
            self.applied_damping=plan['velocity_native_kd_nm_per_rad_s']
            compensation=0.
            commands={0:0.,1:0.}
            ff_limit=0.
        else:
            commands=budget(requests,speeds,command_plan,compensation=compensation)
        kd_step=RATIO**2/128000000
        quantized_kd=math.floor(self.applied_damping/kd_step)*kd_step
        self.previous_net_common=(.5*sum(velocity_info['predicted_net_torque_nm'].values())
            if velocity_info else .5*sum(commands[m]-quantized_kd*speeds[m] for m in (0,1)))
        expected_ff={m:requests[m]+compensation*quantized_kd*speeds[m] for m in (0,1)}
        self.previous_limited=(abs(common_before_friction-recovery)>1e-12 if self.phase in ('PRE_ROLL','RISING') else
                               abs(common_before_friction-balance)>1e-12) or governor_limited or any(
                               abs(commands[m]-expected_ff[m])>1e-12 for m in (0,1))
        if velocity_info:
            self.previous_limited=(abs(common_before_friction-recovery)>1e-12 if self.phase in ('PRE_ROLL','RISING')
                else abs(common_before_friction-balance)>1e-12) or governor_limited or velocity_info['limited']
        stable=(self.phase=='BALANCE' and abs(theta)<=plan['stable_pitch_deg'] and
                abs(rate)<=plan['stable_rate_dps'] and abs(v)<=plan['stable_velocity_m_s'] and
                abs(speeds[0]-speeds[1])<=plan['stable_differential_speed_rad_s'])
        self.stable_since=(a['t'] if self.stable_since is None else self.stable_since) if stable else None
        self.stable_s=a['t']-self.stable_since if self.stable_since is not None else 0.
        self.max_stable_s=max(self.max_stable_s,self.stable_s)
        a['self_righting']=dict(phase=self.phase,elapsed_s=elapsed,rise_elapsed_s=rise_elapsed,
            applied_pitch_rate_limit_dps=rate_limit,
            applied_wheel_speed_limit_rad_s=speed_limit,
            position_derived_wheel_speed_rad_s=position_speeds,
            wheel_position_time_basis=('host_feedback_receive' if plan.get('use_wheel_feedback_timestamps',False) else 'legacy_imu'),
            pre_roll_exit=self.pre_roll_exit,
            best_progress_deg=self.best_progress,
            rolling_velocity_estimate_m_s=v,filtered_velocity_estimate_m_s=self.velocity,
            pitch_target_forward_deg=self.pitch_target,recovery_request_nm=recovery,
            applied_body_damping_nm_per_rad_s=body_damping,
            desired_body_pitch_rate_dps=desired_body_rate,balance_friction_feedforward_nm=friction_ff,
            capture_mix=mix,common_request_nm=common,differential_position_rad=difference,
            differential_correction_nm=correction,command_forward_nm=commands.copy(),
            native_damping_compensation_fraction=compensation,
            native_wheel_damping_nm_per_rad_s=self.applied_damping,
            applied_feedforward_torque_limit_nm=ff_limit,
            velocity_targets_forward_rad_s=self.velocity_targets,
            native_velocity_budget=velocity_info,
            gyro_only_pitch_deg=self.gyro_pitch,rise_polarity=polarity,
            speed_governor_limited=governor_limited,governed_net_request_nm=requests.copy(),
            stable_s=self.stable_s,output_limited=self.previous_limited,
            scope='experimental_motion_control_not_measured_ground_speed_or_self_righting_proof')
        return commands

    def motor_plan(self,plan):
        if self.applied_damping is None:
            raise Fault('motor_plan_before_control')
        if plan.get('native_velocity_control'):
            if self.velocity_targets is None:
                raise Fault('missing_native_velocity_targets')
            speed_limit=plan.get('rise_wheel_speed_limit_rad_s',plan['wheel_speed_limit_rad_s']) if self.phase=='RISING' else plan['wheel_speed_limit_rad_s']
            return dict(plan,native_wheel_damping_nm_per_rad_s=self.applied_damping,
                feedforward_torque_limit_nm=0.,wheel_speed_limit_rad_s=speed_limit,
                velocity_targets_forward_rad_s=self.velocity_targets.copy())
        low=min(plan['native_wheel_damping_nm_per_rad_s'],plan.get('rise_native_wheel_damping_nm_per_rad_s',plan['native_wheel_damping_nm_per_rad_s']))
        high=max(plan['native_wheel_damping_nm_per_rad_s'],plan.get('rise_native_wheel_damping_nm_per_rad_s',plan['native_wheel_damping_nm_per_rad_s']))
        if self.phase=='PRE_ROLL':
            low=high=plan.get('pre_roll_native_wheel_damping_nm_per_rad_s',plan.get('rise_native_wheel_damping_nm_per_rad_s',plan['native_wheel_damping_nm_per_rad_s']))
        finite(self.applied_damping)
        if not low<=self.applied_damping<=high:
            raise Fault('invalid_scheduled_damping')
        speed_limit=plan.get('rise_wheel_speed_limit_rad_s',plan['wheel_speed_limit_rad_s']) if self.phase=='RISING' else plan['wheel_speed_limit_rad_s']
        ff_limit=plan.get('rise_feedforward_torque_limit_nm',plan['feedforward_torque_limit_nm']) if self.phase=='RISING' else plan['feedforward_torque_limit_nm']
        return dict(plan,native_wheel_damping_nm_per_rad_s=self.applied_damping,
                    wheel_speed_limit_rad_s=speed_limit,feedforward_torque_limit_nm=ff_limit)

    def finish(self):
        if self.phase!='BALANCE' or self.stable_s<dict(self.config)['stable_duration_s']:
            self.fault='self_righting_stable_window_not_met'
            self.phase='FAULT'
            raise Fault(self.fault)

    def summary(self):
        return dict(phase=self.phase,fault=self.fault,events=self.events,
                    max_stable_s=self.max_stable_s,ending_stable_s=self.stable_s,
                    best_progress_deg=self.best_progress,automatic_rearm=False,
                    physical_self_righting='NOT_ASSESSED_BY_CONTROLLER',
                    sensor_result_evaluator='analyze_self_righting.py',
                    operator_action_judgment_required=False)


def main(argv=None):
    return trial_main(argv,plan=SELF_RIGHT_PLAN,start_flag='--run-single-self-righting',
                      controller=SelfRightingController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
