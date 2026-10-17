#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Finite ground comparison of the S288 execution layer, no automatic start.

Keep v101 pitch PID, speed reference, differential mix and all guards. The
new adapter uses native velocity damping 0.40, which was exercised in the
suspended fixed-speed diagnostic, instead of merely cancelling a 0.005
passive damper with FF. The host still requests NET torque; no new host
wheel-rate loop or integrator is added. Frozen-input equivalence does not
predict closed-loop stability. Ground effectiveness remains NOT_TESTED.
"""
import struct

from air_trial import main as trial_main
from attitude import Fault,finite
from ground_hold_trial import HoldTravel
from native_velocity_net_adapter import allocate_native_net
from protocol import RATIO,valid_id,crc32_words
from two_deck_velocity_diagnostics import PLAN as BASE,VelocityDiagnosticsController


PLAN=dict(BASE,name='two_deck_native_execution_v113',duration_s=10.,
          native_execution_kd=.40,native_execution_speed_limit_rad_s=6.,
          control_phase='two_deck_native_execution',
          active_message='NATIVE_EXECUTION_ACTIVE: 补偿已开始，红点亮起，最多10秒。保持原姿态控制参数，比较舵机内部速度阻尼；这轮不推碰，手只防倒。仍按每轮0.12Nm、6rad/s、正负30度、70度及原有停止条件执行。')


class NativeExecutionController(VelocityDiagnosticsController):
    config_names=('native_execution_kd','native_execution_speed_limit_rad_s',
                  'feedforward_torque_limit_nm','predicted_net_torque_limit_nm',
                  'wheel_speed_limit_rad_s')

    def reset(self):
        super().reset()
        self.native_allocations={}
        self.native_configuration=None

    def __call__(self,attitude,speeds,plan=PLAN):
        self.native_allocations={}
        config=tuple(plan[k] for k in self.config_names)
        finite(*config)
        kd,rate_limit,ff_limit,net_limit,wheel_limit=config
        if not 0<kd<=1.2 or not 0<rate_limit<=wheel_limit:
            raise Fault('native_execution_configuration_outside_plan')
        if self.native_configuration is not None and config!=self.native_configuration:
            raise Fault('native_execution_configuration_changed')
        self.native_configuration=config
        # The parent computes the checked outer loop and legacy allocation;
        # no I/O occurs here. Discard that allocation before packet creation.
        super().__call__(attitude,speeds,plan)
        info=attitude['ardupilot_balance']
        requests=info['requested_net_per_wheel_nm']
        try:
            allocations={m:allocate_native_net(requests[m],speed,native_kd=kd,
                velocity_limit_rad_s=rate_limit,feedforward_limit_nm=ff_limit,
                net_budget_nm=net_limit,gear_ratio=RATIO) for m,speed in speeds.items()}
        except ValueError as exc:
            raise Fault(str(exc)) from exc
        self.native_allocations=allocations
        self.allocations=allocations
        self.previous_limited=any(a.limited for a in allocations.values())
        commands={m:a.feedforward_nm for m,a in allocations.items()}
        info.update(adapter_limited=self.previous_limited,
            command_forward_nm=commands.copy(),
            predicted_net_forward_nm={m:a.predicted_net_nm for m,a in allocations.items()},
            exact_forward_ff_raw={m:a.feedforward_raw for m,a in allocations.items()},
            exact_native_kd_raw={m:a.native_kd_raw for m,a in allocations.items()},
            exact_forward_velocity_raw={m:a.velocity_raw for m,a in allocations.items()},
            native_velocity_forward_rad_s={m:a.velocity_rad_s for m,a in allocations.items()},
            native_velocity_reference_limited={m:a.velocity_reference_limited for m,a in allocations.items()},
            scope='unchanged_outer_pitch_net_request_native_velocity_execution_experiment')
        return commands

    def allocated_torque_packet(self,mid,sign,command_forward_nm,plan):
        valid_id(mid)
        if type(sign) is not int or sign not in (-1,1) or mid not in self.native_allocations:
            raise Fault('missing_or_invalid_native_allocation')
        if tuple(plan[k] for k in self.config_names)!=self.native_configuration:
            raise Fault('native_execution_configuration_changed_before_packet')
        if tuple(plan[k] for k in self.budget_names)!=self.budget_configuration:
            raise Fault('net_torque_budget_changed_before_packet')
        allocation=self.native_allocations[mid]
        finite(command_forward_nm)
        if command_forward_nm!=allocation.feedforward_nm:
            raise Fault('native_command_changed_before_packet')
        if (abs(allocation.feedforward_nm)>plan['feedforward_torque_limit_nm']+1e-12 or
                abs(allocation.predicted_net_nm)>plan['predicted_net_torque_limit_nm']+1e-12 or
                abs(allocation.velocity_rad_s)>plan['native_execution_speed_limit_rad_s']+1e-12):
            raise Fault('native_packet_outside_budget')
        body=bytes([0xfe,0xee,mid|0x90,0])+struct.pack('<hhihh',
            sign*allocation.feedforward_raw,sign*allocation.velocity_raw,0,0,allocation.native_kd_raw)
        return body+struct.pack('<I',crc32_words(body))


def main(argv=None):
    return trial_main(argv,plan=PLAN,start_flag='--run-two-deck-native-execution',
        controller=NativeExecutionController(),travel_factory=HoldTravel,description=__doc__)


if __name__=='__main__':raise SystemExit(main())
