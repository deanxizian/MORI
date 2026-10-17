# SPDX-License-Identifier: GPL-3.0-or-later
"""MORI adapter: upstream pitch PID requests predicted NET torque, not FF.

The prediction uses the last body-relative shaft rate, not floor velocity.
Firmware dynamics, rate changes and torque calibration can invalidate it;
this is not a hardware torque clamp. No additional wheel-rate PI is enabled.
"""
import math
import struct

from attitude import Fault, finite
from ground_ardupilot_balance import ArduPilotBalanceController
from offline_two_deck_review_20261016.motor_stage import allocate_net_torque
from protocol import RATIO, valid_id, crc32_words


class NetTorquePitchController(ArduPilotBalanceController):
    budget_names=('native_wheel_damping_nm_per_rad_s',
                  'feedforward_torque_limit_nm','predicted_net_torque_limit_nm')

    def reset(self):
        super().reset()
        self.allocations={}
        self.budget_configuration=None

    def __call__(self,attitude,speeds,plan):
        self.allocations={}
        config=tuple(plan[k] for k in self.budget_names)
        finite(*config)
        if self.budget_configuration is None:
            self.budget_configuration=config
        elif config!=self.budget_configuration:
            raise Fault('net_torque_budget_changed')
        # Reuse the numerically checked upstream PID and existing guards.
        # Its legacy FF allocation is discarded below, before any packet I/O.
        super().__call__(attitude,speeds,plan)
        info=attitude['ardupilot_balance']
        requested=info.pop('requested_ff_nm')
        pid_requested=requested
        shaping_limited=False
        if hasattr(self,'shape_common_net_request'):
            requested,shaping_limited=self.shape_common_net_request(requested,attitude,plan)
            finite(requested)
        requests=(self.net_torque_requests(requested,speeds,attitude,plan)
                  if hasattr(self,'net_torque_requests') else {m:requested for m in speeds})
        if set(requests)!=set(speeds):raise Fault('invalid_per_wheel_net_requests')
        finite(*requests.values())
        try:
            allocations={mid:allocate_net_torque(
                requests[mid],speed,native_kd_nm_per_rad_s=config[0],
                feedforward_limit_nm=config[1],net_budget_nm=config[2],
                gear_ratio=RATIO) for mid,speed in speeds.items()}
        except ValueError as exc:
            raise Fault('net_torque_allocation_'+str(exc)) from exc
        commands={mid:a.feedforward_nm for mid,a in allocations.items()}
        self.previous_limited=shaping_limited or any(a.limited for a in allocations.values())
        self.allocations=allocations
        info.update(requested_net_nm=requested,adapter_limited=self.previous_limited,
                    pid_requested_net_nm=pid_requested,
                    requested_net_per_wheel_nm=requests.copy(),
                    command_forward_nm=commands.copy(),
                    predicted_net_forward_nm={m:a.predicted_net_nm for m,a in allocations.items()},
                    exact_forward_ff_raw={m:a.feedforward_raw for m,a in allocations.items()},
                    exact_native_kd_raw={m:a.native_kd_raw for m,a in allocations.items()},
                    scope='upstream_pitch_pid_with_local_predicted_net_torque_adapter')
        return commands

    def allocated_torque_packet(self,mid,sign,command_forward_nm,plan):
        valid_id(mid)
        if type(sign) is not int or sign not in (-1,1) or mid not in self.allocations:
            raise Fault('missing_or_invalid_net_torque_allocation')
        if tuple(plan[k] for k in self.budget_names)!=self.budget_configuration:
            raise Fault('net_torque_budget_changed_before_packet')
        a=self.allocations[mid]
        finite(command_forward_nm)
        if command_forward_nm!=a.feedforward_nm:
            raise Fault('net_torque_command_changed_before_packet')
        raw=sign*a.feedforward_raw
        if (not -32768<=raw<=32767 or not 0<=a.native_kd_raw<=32767 or
                abs(a.feedforward_nm)>plan['feedforward_torque_limit_nm']+1e-12 or
                abs(a.predicted_net_nm)>plan['predicted_net_torque_limit_nm']+1e-12):
            raise Fault('allocated_packet_outside_budget')
        body=bytes([0xfe,0xee,mid|0x90,0])+struct.pack('<hhihh',raw,0,0,0,a.native_kd_raw)
        return body+struct.pack('<I',crc32_words(body))
