"""Opt-in active-only estimate margin/dwell; not a physical torque clamp.

The command/NET budget remains0.12Nm. Default profiles, disabled checks and
zero-FF arming keep their original immediate estimate line. New profiles
explicitly allow up to0.13Nm feedback, stop after50ms continuously above it,
and retain an immediate0.15Nm feedback ceiling in the existing health check.
These are local experimental guards, not vendor current/torque ratings.
"""
from attitude import Fault,finite


class TorqueFeedbackGuard:
    names=('estimated_torque_limit_nm','torque_feedback_soft_nm',
           'torque_feedback_hard_nm','torque_feedback_dwell_s',
           'feedforward_torque_limit_nm','predicted_net_torque_limit_nm',
           'loop_gap_s')

    def __init__(self,plan):
        self.configuration=tuple(plan[k] for k in self.names)
        finite(*self.configuration)
        old,soft,hard,dwell,ff,net,gap=self.configuration
        if (plan.get('active_torque_feedback_guard') is not True or old!=.12 or
                not old<=soft<=.13 or not soft<hard<=.15 or
                not 0<dwell<=.05 or not 0<ff<=.12 or not 0<net<=.12 or
                not 0<gap<=.025):
            raise Fault('torque_feedback_guard_outside_plan')
        self.soft,self.hard,self.dwell,self.gap=soft,hard,dwell,gap
        self.last={};self.since={0:None,1:None};self.failed=False
        self.audit=dict(scope='active_feedback_estimate_only_not_hardware_torque_clamp',
                        old_instant_limit_nm=old,soft_limit_nm=soft,
                        hard_instant_limit_nm=hard,dwell_s=dwell,
                        command_budget_unchanged=True,
                        per_id={m:dict(max_abs_nm=0.,above_original_frames=0,
                                       above_soft_frames=0,max_continuous_soft_s=0.)
                                for m in (0,1)})

    def motor_health_plan(self,plan):
        if (plan.get('active_torque_feedback_guard') is not True or
                tuple(plan[k] for k in self.names)!=self.configuration):
            self.failed=True
            raise Fault('torque_feedback_guard_configuration_changed')
        return dict(plan,estimated_torque_limit_nm=self.hard)

    def observe(self,mid,value,timestamp):
        if self.failed:raise Fault('torque_feedback_guard_latched')
        finite(value,timestamp)
        if type(mid) is not int or mid not in (0,1):
            self.failed=True;raise Fault('torque_feedback_guard_invalid_id')
        if mid in self.last and not 0<timestamp-self.last[mid]<=self.gap:
            self.failed=True;raise Fault('torque_feedback_guard_sample_gap')
        self.last[mid]=timestamp
        value=abs(value);a=self.audit['per_id'][mid]
        a['max_abs_nm']=max(a['max_abs_nm'],value)
        a['above_original_frames']+=int(value>self.configuration[0])
        if value>self.hard:
            self.failed=True;raise Fault('estimated_torque_stop')
        if value<=self.soft:
            self.since[mid]=None
            return
        a['above_soft_frames']+=1
        if self.since[mid] is None:self.since[mid]=timestamp
        elapsed=timestamp-self.since[mid]
        a['max_continuous_soft_s']=max(a['max_continuous_soft_s'],elapsed)
        if elapsed+1e-12>=self.dwell:
            self.failed=True;raise Fault('estimated_torque_sustained_stop')
