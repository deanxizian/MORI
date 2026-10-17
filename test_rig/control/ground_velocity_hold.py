#!/usr/bin/env python3
"""Restrained zero-speed P outer loop around the experimental attitude PD.

Reuse the sign/convention from firmware/motion/v1_2/motion.c: velocity error
sets a bounded pitch reference, and body torque uses pitch minus reference.
Only this test-car entry point uses these experimental gains. No integral,
position hold, navigation command, production enable or automatic restart.
"""
import math

from air_trial import main as trial_main
from attitude import Fault, clip, finite
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from ground_travel_window import TRAVEL_WINDOW_PLAN


VELOCITY_HOLD_PLAN=dict(
    TRAVEL_WINDOW_PLAN,name='restrained_zero_speed_p_outer_loop_v12',
    speed_kp_rad_per_m_s=.25,
    speed_filter_tau_s=.20,
    speed_pitch_reference_limit_deg=1.,
    speed_pitch_reference_slew_dps=2.,
    active_message='RESTRAINED_GROUND_ACTIVE: 零速反馈版开始，最多 30 秒；速度环只小幅调整目标倾角，不超过正负 1 度。请始终轻扶防倒，停机时接住车身；原速度、力矩、温度和转量停止线仍生效。',
)


class VelocityHoldController:
    """A new instance per finite run; no state survives a stop/restart.

    Average signed encoder speed times nominal radius is a velocity proxy,
    not a measured floor speed. It includes body-relative encoder motion,
    tyre deformation and slip; filtering does not qualify this measurement.
    The slow bounded reference does not slew-limit the inner balance torque.
    """
    def __init__(self):
        self.filtered_velocity=0.
        self.pitch_reference_deg=0.
        self.previous_t=None

    def velocity_proxy(self,attitude,forward_wheel_speeds,plan):
        """Default body-relative encoder proxy; subclasses must preserve raw guards."""
        return plan['nominal_wheel_radius_m']*sum(forward_wheel_speeds.values())/2

    def __call__(self,attitude,forward_wheel_speeds,plan=VELOCITY_HOLD_PLAN):
        timestamp=attitude['t']
        dt=attitude['dt'] if self.previous_t is None else timestamp-self.previous_t
        base_error=attitude.get('pitch_error_deg',attitude['pitch_deg'])
        finite(timestamp,dt,base_error,*forward_wheel_speeds.values(),
               self.filtered_velocity,self.pitch_reference_deg)
        if not .001<=dt<=plan['loop_gap_s']:
            raise Fault('velocity_reference_sample_gap')
        if set(forward_wheel_speeds)!={0,1}:
            raise Fault('velocity_reference_requires_both_wheels')
        # Validate raw attitude and wheel limits before updating outer state.
        ground_command(attitude,forward_wheel_speeds,plan)
        raw_proxy=plan['nominal_wheel_radius_m']*(forward_wheel_speeds[0]+forward_wheel_speeds[1])/2
        proxy=self.velocity_proxy(attitude,forward_wheel_speeds,plan)
        finite(proxy)
        target=0.
        if plan.get('allow_position_velocity_target',False):
            target=attitude.get('position_velocity_target_m_s',0.)
            limit=plan['position_speed_limit_m_s']
            finite(target,limit)
            if not 0<limit<=.03 or abs(target)>limit+1e-12:
                raise Fault('position_velocity_target_outside_plan')
        weight=-math.expm1(-dt/plan['speed_filter_tau_s'])
        filtered=self.filtered_velocity+weight*(proxy-self.filtered_velocity)
        desired=clip(math.degrees(plan['speed_kp_rad_per_m_s']*(target-filtered)),
                     plan['speed_pitch_reference_limit_deg'])
        reference=self.pitch_reference_deg+clip(desired-self.pitch_reference_deg,
                                               plan['speed_pitch_reference_slew_dps']*dt)
        reference=clip(reference,plan['speed_pitch_reference_limit_deg'])
        effective_error=base_error-reference
        result=ground_command(dict(attitude,pitch_error_deg=effective_error),
                              forward_wheel_speeds,plan)
        self.filtered_velocity=filtered
        self.pitch_reference_deg=reference
        self.previous_t=timestamp
        # The runner retains this same attitude dictionary before writing;
        # logging makes the moving reference distinct from the fixed zero.
        attitude['velocity_hold']=dict(
            encoder_velocity_proxy_m_s=raw_proxy,control_velocity_proxy_m_s=proxy,
            filtered_velocity_proxy_m_s=filtered,
            target_velocity_m_s=target,
            desired_pitch_reference_deg=desired,pitch_reference_deg=reference,
            effective_pitch_error_deg=effective_error,
        )
        return result


def main(argv=None):
    return trial_main(argv,plan=VELOCITY_HOLD_PLAN,
                      start_flag='--run-restrained-ground-velocity-hold',
                      controller=VelocityHoldController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
