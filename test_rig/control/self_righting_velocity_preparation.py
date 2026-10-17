#!/usr/bin/env python3
"""Native speed feedback only during the bounded reverse preparation.

Preserve trial52's9.5rad/s both-wheel gate,13rad/s independent preparation
stop and0.4s deadline. Convert the existing bounded PRE_ROLL net torque
requests into native targets capped at10rad/s, with quantized-Kd/position
budgeting. Handoff starts from the last predicted native net torque, not an
obsolete FF request. RISING/CAPTURE/BALANCE remain the existing torque path.
No loaded trajectory or hardware torque clamp is inferred. Default inert,
one finite explicit launch, no automatic retry or fault rearm.
"""
import math
from air_trial import main as trial_main
from attitude import Fault,finite
from ground_hold_trial import HoldTravel
from protocol import RATIO
from self_righting_synced_preparation import PLAN as RETIRED_PLAN
from self_righting_supervised import SupervisedRecovery
from velocity_envelope import velocity_targets

PLAN=dict(RETIRED_PLAN,name='first_layer_velocity_preparation_v70',
    preparation_velocity_kd_nm_per_rad_s=.1,
    preparation_velocity_target_limit_rad_s=10.,
    active_message='VELOCITY_PREPARATION_ACTIVE: 第53轮单次起身已启动，最多40秒；仅预滚使用原生速度反馈，目标不超10rad/s，两轮达到9.5后转入原起身控制。预滚13rad/s/0.4s、起身16.5rad/s、净目标0.35Nm、70°C及原有保护保留，不自动重试。')
PLAN.pop('motion_hold_reason')
PLAN['motion_hold_reason']='trial53_preparation_target_not_attained; used launch retired, body still lying per passive IMU'


class VelocityPreparation(SupervisedRecovery):
    def reset(self):
        super().reset()
        self.preparation_targets={0:0.,1:0.}
        self.preparation_active=False

    def validate_arm(self,a,speeds,plan):
        super().validate_arm(a,speeds,plan)
        kd=plan['preparation_velocity_kd_nm_per_rad_s']
        target=plan['preparation_velocity_target_limit_rad_s']
        finite(kd,target)
        if not (0.<kd<=.1 and plan['pre_roll_target_rad_s']<target<plan['pre_roll_speed_limit_rad_s']):
            raise Fault('invalid_preparation_velocity_plan')

    def update(self,a,speeds,plan):
        old_phase=self.phase
        commands=super().update(a,speeds,plan)
        self.preparation_active=self.phase=='PRE_ROLL'
        if not self.preparation_active:
            if old_phase=='PRE_ROLL' and self.phase=='RISING' and self.pre_roll_exit=='time_limit':
                raise Fault('preparation_velocity_not_reached_before_timeout')
            return commands
        state=a['self_righting']
        # Convert the net request actually budgeted by the existing FF path.
        step=RATIO**2/128000000
        old_kd=math.floor(self.applied_damping/step)*step
        requests={m:commands[m]-old_kd*speeds[m] for m in (0,1)}
        p=dict(plan,wheel_speed_limit_rad_s=plan['pre_roll_speed_limit_rad_s'],
            velocity_native_kd_nm_per_rad_s=plan['preparation_velocity_kd_nm_per_rad_s'],
            velocity_target_limit_rad_s=plan['preparation_velocity_target_limit_rad_s'],
            velocity_target_slew_rad_s2=200.)
        rates=state['position_derived_wheel_speed_rad_s']
        self.preparation_targets,info=velocity_targets(requests,speeds,rates,
            self.preparation_targets,a['dt'],p)
        self.applied_damping=p['velocity_native_kd_nm_per_rad_s']
        self.previous_net_common=.5*sum(info['predicted_net_torque_nm'].values())
        self.previous_limited=self.previous_limited or info['limited']
        self.last_commands={0:0.,1:0.}
        state.update(command_forward_nm={0:0.,1:0.},
            preparation_native_velocity=True,
            velocity_targets_forward_rad_s=self.preparation_targets.copy(),
            native_velocity_budget=info,
            native_damping_compensation_fraction=0.,
            native_wheel_damping_nm_per_rad_s=self.applied_damping,
            applied_feedforward_torque_limit_nm=0.)
        return self.last_commands.copy()

    def motor_plan(self,plan):
        if self.phase=='PRE_ROLL' and self.preparation_active:
            return dict(plan,native_velocity_control=True,
                wheel_speed_limit_rad_s=plan['pre_roll_speed_limit_rad_s'],
                velocity_targets_forward_rad_s=self.preparation_targets.copy(),
                velocity_target_limit_rad_s=plan['preparation_velocity_target_limit_rad_s'],
                native_wheel_damping_nm_per_rad_s=self.applied_damping,
                feedforward_torque_limit_nm=0.)
        return super().motor_plan(plan)


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-velocity-preparation',
        controller=VelocityPreparation(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
