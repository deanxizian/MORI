#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite relative encoder-position -> velocity -> pitch -> net-torque trial.

Uses the preserved v88 PID/heading baseline, not the unsuccessful lower-I
comparison. The local position P supplies a small return speed to the existing
speed-to-pitch reference. Nominal wheel-radius odometry has no slip correction
or world reference; this is a prototype return-to-start proxy, not navigation.
No automatic rearm, background operation, or larger actuator/tilt limits.
"""
from air_trial import main as trial_main
from attitude import Fault,clip,finite
from ground_hold_trial import HoldTravel
from ground_trial import ground_command
from two_deck_heading_hold import PLAN as BASE,RelativeHeadingController

PLAN=dict(BASE,name='two_deck_relative_position_hold_v90',
          allow_position_velocity_target=True,
          position_speed_kp_per_s=.5,position_speed_limit_m_s=.03,
          active_message='POSITION_BALANCE_ACTIVE: 起点回中版平衡补偿已开始，红点亮起。相对起点位移产生最多3厘米每秒的回中速度目标，仍为最多30秒及原停止条件；请只轻扶防倒。')


def update_position_reference(state,attitude,speeds,plan):
    """Shared original position-P reference; never sends a motor command.

    The caller owns a fresh origin/configuration per explicitly armed run.
    Keep the previously exercised sign, caps and raw guard order unchanged.
    This is relative encoder return, not measured world-position holding.
    """
    ground_command(attitude,speeds,plan)
    positions=attitude.get('wheel_position_forward_rad')
    if not isinstance(positions,dict) or set(positions)!={0,1}:
        raise Fault('position_hold_requires_both_encoders')
    config=tuple(plan[k] for k in ('position_speed_kp_per_s','position_speed_limit_m_s','nominal_wheel_radius_m'))
    finite(*config,*positions.values())
    kp,limit,radius=config
    if not 0<kp<=.75 or not 0<limit<=.03 or not 0<radius<=.05:
        raise Fault('position_hold_configuration_outside_plan')
    if state.position_configuration is not None and config!=state.position_configuration:
        raise Fault('position_hold_configuration_changed')
    state.position_configuration=config
    position=radius*(positions[0]+positions[1])/2
    if state.position_origin is None:state.position_origin=position
    error=position-state.position_origin
    target=clip(-kp*error,limit)
    attitude['position_velocity_target_m_s']=target
    attitude['position_hold']=dict(encoder_position_proxy_m=position,
        origin_proxy_m=state.position_origin,relative_error_proxy_m=error,
        target_velocity_m_s=target,scope='nominal_radius_encoder_proxy_not_world_position')


class PositionHoldController(RelativeHeadingController):
    def reset(self):
        super().reset()
        self.position_origin=None
        self.position_configuration=None

    def __call__(self,attitude,speeds,plan=PLAN):
        self.allocations={}
        update_position_reference(self,attitude,speeds,plan)
        return super().__call__(attitude,speeds,plan)


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-position',
                      controller=PositionHoldController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
