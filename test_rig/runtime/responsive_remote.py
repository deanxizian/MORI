# SPDX-License-Identifier: GPL-3.0-or-later
"""Derived v184 remote lifecycle with bounded faster driving references.

Standing feedback, stop handling, integral anti-windup and torque allocation
remain on the original path. Runtime target caps are explicit below.
"""
import math
from ground_trial import ground_command
from two_deck_live_causal_velocity import CausalVelocityReference
from motion_limits import (MAX_DRIVE_M_S, MAX_TURN_RAD_S, TURN_ACCEL_RAD_S2,
                           DRIVE_PITCH_SLEW_DPS, coupled_reference)
from attitude import Fault, clip, finite
from two_deck_remote_drive import (PLAN, RemoteDriveController as FrozenController,
                                   NativeDampingController, RemoteVelocityReference)


class ResponsiveVelocityReference(RemoteVelocityReference):
    def __call__(self, attitude, speeds, plan):
        intent = attitude.get('remote_desired_velocity_m_s', 0.)
        target = attitude.get('remote_velocity_target_m_s', 0.)
        sign = 1 if intent > 0 else -1 if intent < 0 else 0
        quicker = (intent * target > 0 and not attitude.get('remote_stopping', False)
                   and sign * self.filtered_velocity >= -.015)
        selected = dict(plan, speed_kp_rad_per_m_s=.50,
                        speed_pitch_reference_slew_dps=DRIVE_PITCH_SLEW_DPS) if quicker else plan
        result = self._bounded_remote_call(attitude, speeds, selected)
        attitude['velocity_hold'].update(
            responsive_drive_active=quicker,
            selected_speed_gain=selected['speed_kp_rad_per_m_s'],
            selected_pitch_slew_dps=selected['speed_pitch_reference_slew_dps'])
        return result

    # Derived from frozen RemoteVelocityReference.__call__; only target cap
    # and explicit base dispatch change. No measurement rescaling.
    def _bounded_remote_call(self,a,speeds,plan):
        previous_reference,previous_t=self.pitch_reference_deg,self.previous_t
        result=CausalVelocityReference.__call__(self,a,speeds,plan)
        if 'remote_velocity_target_m_s' not in a:
            self.remote_speed_integral_rad=0.
            return result
        target=a['remote_velocity_target_m_s'];finite(target)
        if abs(target)>MAX_DRIVE_M_S+1e-12:raise Fault('remote_velocity_target_outside_plan')
        dt=a['dt'] if previous_t is None else a['t']-previous_t
        error_v=target-self.filtered_velocity
        old_i=self.remote_speed_integral_rad
        candidate=clip(old_i+.20*error_v*dt,math.radians(.75))
        stopping=bool(a.get('remote_stopping',False))
        transitioning=bool(a.get('remote_reference_transition',False))
        if transitioning:candidate=old_i
        if stopping:
            # Remove driving trim smoothly while braking to zero speed;
            # do not keep building a new bias during this handover.
            candidate=old_i*math.exp(-dt/.20)
            if abs(candidate)<1e-9:candidate=0.
        p_term=plan['speed_kp_rad_per_m_s']*error_v
        requested=p_term+candidate
        pitch_limit=math.radians(plan['speed_pitch_reference_limit_deg'])
        # Do not integrate further into a saturated body request or pitch cap.
        # Opposing error can always unwind the stored remote bias.
        growing=abs(candidate)>abs(old_i) and candidate*old_i>=0
        blocked=a.get('remote_body_limited',False) or (abs(requested)>pitch_limit and requested*error_v>0)
        if not (blocked and growing):self.remote_speed_integral_rad=candidate
        desired=clip(math.degrees(p_term+self.remote_speed_integral_rad),
                     plan['speed_pitch_reference_limit_deg'])
        reference=previous_reference+clip(desired-previous_reference,
                                         plan['speed_pitch_reference_slew_dps']*dt)
        reference=clip(reference,plan['speed_pitch_reference_limit_deg'])
        error=a.get('pitch_error_deg',a['pitch_deg'])-reference
        result=ground_command(dict(a,pitch_error_deg=error),speeds,plan)
        self.pitch_reference_deg=reference
        a['velocity_hold'].update(target_velocity_m_s=target,
            desired_pitch_reference_deg=desired,pitch_reference_deg=reference,
            effective_pitch_error_deg=error,remote_driving_reference=True,
            remote_speed_integral_deg=math.degrees(self.remote_speed_integral_rad),
            remote_speed_integral_blocked=bool(blocked and growing),
            remote_speed_integral_held_for_transition=bool(transitioning and not stopping))
        return result

class ResponsiveRemoteController(FrozenController):
    def __call__(self,a,speeds,plan=PLAN):
        dt=a['dt'];finite(dt)
        if not 0<dt<=plan['loop_gap_s']:raise Fault('remote_invalid_dt')
        row=self.keys.read(a['t'])
        if row[1] and not row[2] and row[3]==0:self.remote_gate=True
        forward,right=(row[4],row[5]) if self.remote_gate else (0,0)
        target_v=MAX_DRIVE_M_S*forward;target_turn=MAX_TURN_RAD_S*right
        old_v,old_turn=self.remote_v,self.remote_turn
        self.remote_v=self.drive_profile.update(target_v,dt)
        # Quicker turn acceleration; release/opposite-direction braking
        # retain the original 6 rad/s^2 reference slew.
        accelerating_turn = target_turn * old_turn >= 0 and abs(target_turn) > abs(old_turn)
        turn_slew = TURN_ACCEL_RAD_S2 if accelerating_turn else 6.
        self.remote_turn += clip(target_turn-self.remote_turn,turn_slew*dt)
        self.remote_v, self.remote_turn = coupled_reference(
            old_v, old_turn, self.remote_v, self.remote_turn,
            plan['nominal_wheel_radius_m'])
        self.drive_profile.velocity = self.remote_v
        a['remote_desired_velocity_m_s'] = target_v
        p=a.get('wheel_position_forward_rad',{})
        if set(p)!={0,1}:raise Fault('remote_requires_encoders')
        finite(*p.values())
        position=plan['nominal_wheel_radius_m']*(p[0]+p[1])/2;difference=p[0]-p[1]
        if self.remote_heading_start is None:self.remote_heading_start=difference
        # A turn commands zero mean forward velocity, independently of the
        # differential rate. Never keep chasing an old pre-turn position.
        if self.remote_v or old_v or self.remote_turn or old_turn:
            self.position_origin=position+self.remote_v/plan['position_speed_kp_per_s']
            a['remote_velocity_target_m_s']=self.remote_v
            # Brake trim from key release, not only after the shaped reference
            # reaches zero; avoid integrating a changing acceleration target.
            a['remote_stopping']=forward==0
            a['remote_reference_transition']=abs(target_v-self.remote_v)>.01
            a['remote_body_limited']=self.previous_limited or abs(self.remote_last_common_nm)>=plan['predicted_net_torque_limit_nm']-1e-9
            self.remote_started=True
            self.remote_stopping=True;self.remote_stop_settle_s=0.
        elif self.remote_stopping:
            # A zero reference starts braking, not instantaneous physical
            # stopping. Capture the location only after the measured speed
            # settles, so position return cannot pull back to a premature
            # release point. This preserves the idle PID and its state.
            self.position_origin=position
            a['remote_velocity_target_m_s']=0.
            a['remote_stopping']=True
            raw_mean=plan['nominal_wheel_radius_m']*(speeds[0]+speeds[1])/2
            settled=(abs(self.speed_reference.filtered_velocity)<.01 and
                     abs(raw_mean)<.015 and abs(a['pitch_rate_dps'])<10.)
            self.remote_stop_settle_s=self.remote_stop_settle_s+dt if settled else 0.
            if self.remote_stop_settle_s>=.30:self.remote_stopping=False
        if self.remote_turn or old_turn:
            if old_turn==0 or self.heading_origin is None:
                self.heading_origin=difference
                self.remote_expected_turn_rad=difference-self.remote_heading_start
            self.heading_origin+=self.remote_turn*dt
            self.heading_origin=difference+clip(self.heading_origin-difference,.35)
            self.remote_expected_turn_rad+=self.remote_turn*dt
            if self.remote_turn==0:
                self.heading_origin=difference
                self.remote_expected_turn_rad=difference-self.remote_heading_start
            self.remote_started=True
        self.remote_status=dict(input_reason=row[6],connected=row[1],held_mask=row[3],
            gate_open=self.remote_gate,forward_key=forward,right_key=right,
            commanded_velocity_m_s=self.remote_v,commanded_wheel_difference_rad_s=self.remote_turn,
            expected_turn_difference_rad=self.remote_expected_turn_rad,
            stopping_before_position_hold=self.remote_stopping,
            stop_settle_s=self.remote_stop_settle_s,
            drive_profile_lead_m_s=self.drive_profile.lead,
            forward_reference_released=forward==0,turn_reference_slew_rad_s2=turn_slew,
            scope='nominal reference, not measured floor speed or calibrated yaw',
            input_worker=self.keys.diagnostics.copy(),input_age_s=max(0.,a['t']-self.keys.value[0]))
        a['remote_drive']=self.remote_status.copy()
        return NativeDampingController.__call__(self,a,speeds,plan)
