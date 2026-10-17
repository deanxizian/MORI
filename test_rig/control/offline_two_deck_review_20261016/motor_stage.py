# SPDX-License-Identifier: GPL-3.0-or-later
"""Offline-only motor-stage study; no device imports, packets or run entry.

Throttle shaping follows pinned ArduPilot AP_MotorsUGV::get_scaled_throttle.
Wheel-rate math reuses the existing numerically checked AC_PID subset via
BalancePitchPID with all pitch-specific feedforward/limit features disabled.
The S288 net-torque allocator is local adapter math, NOT ArduPilot code or
a hardware torque clamp. Parameters require later physical characterization.
"""
from dataclasses import dataclass
import math

from ardupilot_balance_core import BalancePitchPID


def scaled_throttle_pct(throttle_pct, minimum_pct, expo):
    """Upstream order: minimum throttle first, then inverse thrust curve.

    Input/output units are PERCENT, not Nm, rad/s, or normalized +/-1.
    Valid-input parity only; this wrapper rejects invalid configurations.
    A nonzero minimum creates a discontinuity at zero as upstream does;
    no minimum is inferred from old unloaded breakaway measurements.
    """
    if not all(math.isfinite(v) for v in (throttle_pct, minimum_pct, expo)):
        raise ValueError('nonfinite_throttle_input')
    if not -100. <= throttle_pct <= 100. or not 0. <= minimum_pct <= 100. or not -1. <= expo <= 1.:
        raise ValueError('throttle_input_outside_contract')
    if abs(throttle_pct) < 1.1920928955078125e-7:
        return throttle_pct
    sign = -1. if throttle_pct < 0 else 1.
    scaled = sign * minimum_pct + throttle_pct * (1. - minimum_pct / 100.)
    if expo == 0.:
        return scaled
    value = max(-1., min(1., scaled / 100.))
    return 100. * sign * ((expo - 1.) + math.sqrt(max(0., (1. - expo)**2 + 4. * expo * abs(value)))) / (2. * expo)


@dataclass(frozen=True)
class RateGains:
    max_rate_rad_s: float
    kp_pct_per_rad_s: float
    ki_pct_per_rad: float
    kd_pct_per_rad_s2: float
    ff_pct_per_rad_s: float
    integral_limit_pct: float
    target_filter_hz: float = 0.
    error_filter_hz: float = 0.
    derivative_filter_hz: float = 0.

    def __post_init__(self):
        if not all(math.isfinite(v) and v >= 0 for v in vars(self).values()) or self.max_rate_rad_s <= 0:
            raise ValueError('invalid_rate_gains_or_zero_rate_max')


class WheelRateStage:
    """One explicit state per wheel, with percent-to-rad/s-to-percent units.

    AP_WheelRateControl's actual implementation returns PERCENT despite some
    parameter comments saying -1..1. No rate_max=0 stopping mode or automatic
    timeout reset is emulated: the future hardware wrapper must fault-stop
    on unhealthy/stale feedback and instantiate a fresh stage after unlock.
    Native S288 velocity control must not be silently stacked under this loop.
    """
    def __init__(self, gains):
        self.gains = gains
        self.pid = BalancePitchPID(
            kp=gains.kp_pct_per_rad_s, ki=gains.ki_pct_per_rad,
            kd=gains.kd_pct_per_rad_s2, imax=gains.integral_limit_pct,
            ff=gains.ff_pct_per_rad_s, pitch_ff=0., pitch_max=1.,
            limit_tc=0., limit_threshold=0.,
            fltt=gains.target_filter_hz, flte=gains.error_filter_hz,
            fltd=gains.derivative_filter_hz,
        )
        self.previous_limited = False

    def update(self, desired_rate_pct, actual_rate_rad_s, dt, *, downstream_limited=False):
        if not all(math.isfinite(v) for v in (desired_rate_pct, actual_rate_rad_s, dt)) or not .001 <= dt <= .025:
            raise ValueError('invalid_rate_sample_or_gap')
        if abs(desired_rate_pct) > 100.:
            raise ValueError('rate_request_outside_percent_contract')
        desired_rate = desired_rate_pct * .01 * self.gains.max_rate_rad_s
        output_pct = self.pid.update(desired_rate, actual_rate_rad_s, dt,
                                     self.previous_limited or downstream_limited)
        self.previous_limited = abs(output_pct) >= 100.
        return dict(desired_rate_rad_s=desired_rate,
                    raw_output_pct=output_pct,
                    bounded_output_normalized=max(-1., min(1., output_pct / 100.)),
                    limited=self.previous_limited,
                    pid=dict(self.pid.info))


@dataclass(frozen=True)
class TorqueAllocation:
    feedforward_raw: int
    native_kd_raw: int
    feedforward_nm: float
    predicted_net_nm: float
    requested_net_nm: float
    limited: bool
    torque_lsb_nm: float


def allocate_net_torque(requested_net_nm, body_relative_rate_rad_s, *,
                        native_kd_nm_per_rad_s, feedforward_limit_nm,
                        net_budget_nm, gear_ratio):
    """Separate requested NET output from protocol FF minus native damping.

    Intersect limits on the actual integer command grid; return raw integers
    so a future packet wrapper cannot truncate a decoded float a second time.
    This predicts torque only at the supplied shaft rate. Changing rate,
    firmware dynamics and motor calibration can invalidate that prediction.
    """
    values = (requested_net_nm, body_relative_rate_rad_s, native_kd_nm_per_rad_s,
              feedforward_limit_nm, net_budget_nm, gear_ratio)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('nonfinite_torque_allocation')
    if min(feedforward_limit_nm, net_budget_nm, gear_ratio) <= 0 or native_kd_nm_per_rad_s < 0:
        raise ValueError('invalid_torque_allocation_budget')
    torque_lsb = gear_ratio / 256000.
    kd_lsb = gear_ratio**2 / 128000000.
    kd_raw = math.floor(native_kd_nm_per_rad_s / kd_lsb)
    damping = kd_raw * kd_lsb * body_relative_rate_rad_s
    lower = max(-feedforward_limit_nm, -net_budget_nm + damping)
    upper = min(feedforward_limit_nm, net_budget_nm + damping)
    raw_min, raw_max = math.ceil(lower / torque_lsb), math.floor(upper / torque_lsb)
    if raw_min > raw_max:
        raise ValueError('no_feasible_integer_torque_command')
    wanted_raw = round((requested_net_nm + damping) / torque_lsb)
    raw = max(raw_min, min(raw_max, wanted_raw))
    if not -32768 <= raw <= 32767 or not 0 <= kd_raw <= 32767:
        raise ValueError('allocation_exceeds_protocol_fields')
    ff = raw * torque_lsb
    return TorqueAllocation(raw, kd_raw, ff, ff - damping,
                            requested_net_nm, raw != wanted_raw, torque_lsb)
