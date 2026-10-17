#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite MORI trial using an explicitly scaled ArduPilot Balance Bot PID port.

Manual-mode equivalent: fixed pitch trim, no navigation or outer speed loop.
S288 packets/native damping and every v12 stop condition are retained.
No hardware is opened by default; one operator unlock allows one finite run.
Parameters below are MORI experimental values, not ArduPilot defaults and not
validated balance gains. Normalized output 1 is mapped to 0.12 Nm FF only.
"""
import math

from air_trial import main as trial_main
from ardupilot_balance_core import BalancePitchPID
from attitude import Fault, finite
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from ground_travel_window import TRAVEL_WINDOW_PLAN
from protocol import RATIO


ARDUPILOT_PLAN=dict(
    TRAVEL_WINDOW_PLAN,name='restrained_ardupilot_balancebot_pid_port_v13',
    duration_s=15.,control_phase='ground_ardupilot_pid',
    ardupilot_ref='Rover-4.7.2',
    ardupilot_commit='fb773567896014da007bca58358704d4a0d8516f',
    output_scale_nm=.12,
    # Keep the previously tested physical P/D scales. Only the port's
    # normalized gains divide by output_scale_nm. No vendor PWM -> Nm guess.
    ap_kp=3./.12,ap_ki=.6/.12,ap_kd=.05/.12,ap_imax=.02/.12,
    ap_fltt_hz=0.,ap_flte_hz=0.,ap_fltd_hz=10.,
    ap_ff=0.,ap_dff=0.,ap_pitch_ff=0.,
    ap_pitch_max_deg=5.,ap_limit_tc_s=.5,ap_limit_threshold=.6,
    pitch_trim_forward_deg=0.,
    active_message='RESTRAINED_GROUND_ACTIVE: ArduPilot 平衡控制逻辑适配版开始，最多 15 秒；请轻扶防倒，先让它自行纠偏。保留 0.12 Nm、约 115 度/秒、70 度和原转量等停止条件。',
)


class ArduPilotBalanceController:
    """Local I/O adapter; the PID port itself has no access to devices.

    Encoder rates remain in guards and in native-damper output budgeting.
    This trial deliberately isolates pitch control as upstream Manual tuning
    recommends. It does not claim wheel-rate/position hold or full ArduPilot.
    """
    def __init__(self):
        self.reset()

    def reset(self):
        self.pid=None
        self.previous_t=None
        self.previous_limited=False
        self.configuration=None

    @staticmethod
    def configuration_values(plan):
        names=('output_scale_nm','ap_kp','ap_ki','ap_kd','ap_imax',
               'ap_fltt_hz','ap_flte_hz','ap_fltd_hz','ap_ff','ap_dff',
               'ap_pitch_ff','ap_pitch_max_deg','ap_limit_tc_s',
               'ap_limit_threshold','pitch_trim_forward_deg')
        return tuple(plan[k] for k in names)+(
            plan.get('allow_speed_pitch_reference',False),
            plan.get('allow_wide_speed_pitch_reference',False),
            plan.get('speed_pitch_reference_limit_deg',0.),
            plan.get('ap_smax',0.),plan.get('ap_slew_tau_s',1.),
            plan.get('ap_slew_min_modifier',0.))

    def apply_live_gains(self,before,after):
        """Explicit opt-in path: preserve I/filter state and every non-gain field.

        Ordinary __call__ still rejects changed parameters. Only the bounded
        live controller calls this method, with a small interpolated step at
        a control boundary; no worker thread touches PID state.
        """
        from live_tuning_policy import validate_plan_change
        try:validate_plan_change(before,after)
        except (ValueError,KeyError,TypeError) as exc:
            raise Fault('live_gain_change_'+str(exc)) from exc
        if self.pid is None or self.configuration_values(before)!=self.configuration:
            raise Fault('live_gain_change_wrong_controller_state')
        self.pid.kp,self.pid.ki,self.pid.kd=after['ap_kp'],after['ap_ki'],after['ap_kd']
        self.configuration=self.configuration_values(after)

    def __call__(self,attitude,forward_wheel_speeds,plan=ARDUPILOT_PLAN):
        # Evaluate the already validated raw guards before processing state.
        ground_command(attitude,forward_wheel_speeds,plan)
        if set(forward_wheel_speeds)!={0,1}:
            raise Fault('ardupilot_requires_both_wheel_feedbacks')
        timestamp=attitude['t']
        dt=attitude['dt'] if self.previous_t is None else timestamp-self.previous_t
        finite(timestamp,dt)
        if not .001 <= dt <= plan['loop_gap_s']:
            raise Fault('ardupilot_sample_gap')
        config=self.configuration_values(plan)
        finite(*config)
        scale=plan['output_scale_nm']
        if scale <= 0 or scale > plan['feedforward_torque_limit_nm']:
            raise Fault('ardupilot_output_scale_outside_plan')
        if (plan['ap_imax']*scale > .0200000001 or
                abs(plan['pitch_trim_forward_deg']) > 1.):
            raise Fault('ardupilot_integral_or_trim_outside_plan')
        if plan.get('ap_smax',0.)>0:
            if (not plan.get('allow_pd_slew_modifier') is True or
                    not .25<=plan['ap_smax']*scale<=4. or
                    not .5<=plan.get('ap_slew_tau_s',1.)<=2. or
                    not .5<=plan.get('ap_slew_min_modifier',0.)<=1.):
                raise Fault('pd_slew_modifier_outside_experimental_plan')
        if self.pid is None:
            self.configuration=config
            self.pid=BalancePitchPID(
                kp=plan['ap_kp'],ki=plan['ap_ki'],kd=plan['ap_kd'],imax=plan['ap_imax'],
                fltt=plan['ap_fltt_hz'],flte=plan['ap_flte_hz'],fltd=plan['ap_fltd_hz'],
                ff=plan['ap_ff'],dff=plan['ap_dff'],pitch_ff=plan['ap_pitch_ff'],
                pitch_max=math.radians(plan['ap_pitch_max_deg']),
                limit_tc=plan['ap_limit_tc_s'],limit_threshold=plan['ap_limit_threshold'],
                smax=plan.get('ap_smax',0.),slew_tau=plan.get('ap_slew_tau_s',1.),
                slew_min_modifier=plan.get('ap_slew_min_modifier',0.))
        elif config != self.configuration:
            raise Fault('ardupilot_parameters_changed_during_run')
        # MORI positive pitch is forwards; upstream positive pitch backwards.
        actual=-math.radians(attitude['pitch_deg'])
        desired_pitch=plan['pitch_trim_forward_deg']
        if plan.get('allow_speed_pitch_reference',False):
            correction=attitude.get('speed_pitch_reference_deg',0.)
            limit=plan['speed_pitch_reference_limit_deg']
            finite(correction,limit)
            maximum=3. if plan.get('allow_wide_speed_pitch_reference') is True else 1.
            if not 0.<limit<=maximum or abs(correction)>limit+1e-12:
                raise Fault('speed_pitch_reference_outside_plan')
            desired_pitch+=correction
        target=-math.radians(desired_pitch)
        motor_limit=self.previous_limited
        if hasattr(self,'pitch_integrator_limit'):
            motor_limit=bool(self.pitch_integrator_limit(attitude,forward_wheel_speeds,plan,target,actual)) or motor_limit
        slew_clock=dict(now_ms=int(timestamp*1000)&0xffffffff) if self.pid.slew is not None else {}
        output=self.pid.update(target,actual,dt,motor_limit,**slew_clock)
        requested=output*scale
        # Preserve the packet-quantization-aware native damping envelope.
        kd_step=RATIO**2/128000000
        native_kd=math.floor(plan['native_wheel_damping_nm_per_rad_s']/kd_step)*kd_step
        cap=plan['predicted_net_torque_limit_nm']-RATIO/256000
        commands={}
        for mid,speed in forward_wheel_speeds.items():
            damping=native_kd*speed
            low=max(-plan['feedforward_torque_limit_nm'],-cap+damping)
            high=min(plan['feedforward_torque_limit_nm'],cap+damping)
            if low > high:
                raise Fault('native_braking_envelope_unavailable')
            commands[mid]=max(low,min(high,requested))
        limited=any(abs(v-requested)>1e-12 for v in commands.values())
        attitude['ardupilot_balance']=dict(
            **self.pid.info,desired_pitch_forward_deg=desired_pitch,
            output_scale_nm=scale,requested_ff_nm=requested,
            p_nm=self.pid.info['p']*scale,i_nm=self.pid.info['i']*scale,
            d_nm=self.pid.info['d']*scale,ff_nm=(self.pid.info['ff']+self.pid.info['pitch_ff'])*scale,
            adapter_limited=limited,command_forward_nm=commands.copy(),
            wheel_rate_forward_rad_s=forward_wheel_speeds.copy(),
            scope='ported_pitch_controller_manual_tuning_not_full_ardupilot')
        self.previous_limited=limited
        self.previous_t=timestamp
        return commands


def main(argv=None):
    return trial_main(argv,plan=ARDUPILOT_PLAN,
                      start_flag='--run-restrained-ardupilot-balance',
                      controller=ArduPilotBalanceController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':
    raise SystemExit(main())
