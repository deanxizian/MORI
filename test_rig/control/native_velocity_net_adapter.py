# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental S288 execution adapter; no I/O and no wheel-rate integrator.

Official hybrid law: torque = FF + Kd * (desired_rate - measured_rate).
Encode the existing NET request using a velocity reference near the last
measured rate, with FF correcting wire quantization. This leaves the sampled
NET request approximately unchanged, while increasing damping between host
updates. It is NOT the fixed-speed diagnostic, a hardware torque clamp, or
an established improvement in balance. Motor/sensor delay remains unknown.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class NativeNetAllocation:
    feedforward_raw: int
    velocity_raw: int
    native_kd_raw: int
    feedforward_nm: float
    velocity_rad_s: float
    predicted_net_nm: float
    requested_net_nm: float
    limited: bool
    velocity_reference_limited: bool
    torque_lsb_nm: float


def allocate_native_net(requested_net_nm, measured_rate_rad_s, *, native_kd,
                        velocity_limit_rad_s, feedforward_limit_nm,
                        net_budget_nm, gear_ratio):
    values=(requested_net_nm,measured_rate_rad_s,native_kd,velocity_limit_rad_s,
            feedforward_limit_nm,net_budget_nm,gear_ratio)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('nonfinite_native_net_allocation')
    if min(values[2:])<=0:
        raise ValueError('invalid_native_net_budget')
    torque_lsb=gear_ratio/256000.
    speed_lsb=math.tau/(gear_ratio*2.56)
    kd_lsb=gear_ratio**2/128000000.
    kd_raw=math.floor(native_kd/kd_lsb)
    speed_max_raw=math.floor(velocity_limit_rad_s/speed_lsb)
    if not 1<=kd_raw<=32767 or not 1<=speed_max_raw<=32767:
        raise ValueError('native_net_protocol_range')
    kd=kd_raw*kd_lsb
    bounded_request=max(-net_budget_nm,min(net_budget_nm,requested_net_nm))
    wanted_velocity_raw=round((measured_rate_rad_s+bounded_request/kd)/speed_lsb)
    velocity_raw=max(-speed_max_raw,min(speed_max_raw,wanted_velocity_raw))
    velocity=velocity_raw*speed_lsb
    native_term=kd*(velocity-measured_rate_rad_s)
    # Intersect FF and NET bounds on the exact wire integer grid.
    raw_min=math.ceil(max(-feedforward_limit_nm,-net_budget_nm-native_term)/torque_lsb)
    raw_max=math.floor(min(feedforward_limit_nm,net_budget_nm-native_term)/torque_lsb)
    if raw_min>raw_max:
        raise ValueError('no_feasible_native_net_command')
    wanted_ff_raw=round((bounded_request-native_term)/torque_lsb)
    ff_raw=max(raw_min,min(raw_max,wanted_ff_raw))
    if not -32768<=ff_raw<=32767:
        raise ValueError('native_net_protocol_range')
    ff=ff_raw*torque_lsb
    return NativeNetAllocation(ff_raw,velocity_raw,kd_raw,ff,velocity,
        ff+native_term,requested_net_nm,
        bounded_request!=requested_net_nm or ff_raw!=wanted_ff_raw,
        velocity_raw!=wanted_velocity_raw,torque_lsb)
