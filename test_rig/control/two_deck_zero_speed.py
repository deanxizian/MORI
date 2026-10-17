#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite upright balance with the existing slow zero-speed reference layer.

Reuses ground_velocity_hold's tested sign/filter/slew logic, now feeding the
ArduPilot pitch PID and exact NET allocator. The bounded reference follows
the speed-to-pitch cascade in the pinned Rover mode.cpp/balance_bot.cpp.
This local encoder proxy is not ArduPilot AHRS speed or a ground-speed sensor.
No position hold, automatic trim, swing-up, gain change, or automatic rearm.
"""
from air_trial import main as trial_main
from ground_hold_trial import HoldTravel
from ground_velocity_hold import VELOCITY_HOLD_PLAN,VelocityHoldController
from net_torque_adapter import NetTorquePitchController
from two_deck_cued_balance import PLAN as BASE

PLAN=dict(BASE,name='two_deck_red_cue_zero_speed_v86',allow_speed_pitch_reference=True,
          control_phase='two_deck_zero_speed_net_pid',
          **{k:VELOCITY_HOLD_PLAN[k] for k in (
              'speed_kp_rad_per_m_s','speed_filter_tau_s',
              'speed_pitch_reference_limit_deg','speed_pitch_reference_slew_dps')})
PLAN['active_message']='ZERO_SPEED_BALANCE_ACTIVE: 平衡补偿已开始，下方红点亮起。新增零速反馈，缓慢调整目标倾角最多正负1度；请只防倒，让车身和两轮能小幅前后活动。最多30秒，原停止条件保留。'


class ZeroSpeedNetController(NetTorquePitchController):
    def reset(self):
        super().reset()
        self.speed_reference=VelocityHoldController()

    def __call__(self,attitude,speeds,plan=PLAN):
        # Reuse the existing reference computation. Its old PD output is
        # deliberately discarded; only the reviewed PID/net allocation below
        # owns the packet sent to the motors. Raw guards are still evaluated.
        self.speed_reference(attitude,speeds,plan)
        attitude['speed_pitch_reference_deg']=attitude['velocity_hold']['pitch_reference_deg']
        return super().__call__(attitude,speeds,plan)


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-zero-speed',
                      controller=ZeroSpeedNetController(),travel_factory=HoldTravel,
                      description=__doc__)


if __name__=='__main__':raise SystemExit(main())
