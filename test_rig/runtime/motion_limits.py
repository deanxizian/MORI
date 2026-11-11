# SPDX-License-Identifier: GPL-3.0-or-later
"""Runtime reference limits, independent of the frozen physical stop guards."""
import math
from attitude import Fault, finite

MAX_DRIVE_M_S = .16
MAX_TURN_RAD_S = 5.
MAX_REFERENCE_WHEEL_RAD_S = 5.
DRIVE_ACCEL_M_S2 = .40
TURN_ACCEL_RAD_S2 = 16.
DRIVE_PITCH_SLEW_DPS = 12.


def coupled_reference(old_v, old_turn, candidate_v, candidate_turn, radius):
    """Allocate only magnitude increases; let braking finish without starvation.

    Each output lies between that axis's old and candidate values, so the
    caller's slew limits survive. The L1 envelope bounds both wheel references.
    This is reference allocation, not a measured shaft speed or torque guard.
    """
    finite(old_v, old_turn, candidate_v, candidate_turn, radius)
    if radius <= 0:
        raise Fault('remote_invalid_wheel_radius')
    old = (old_v / radius, old_turn / 2.)
    candidate = (candidate_v / radius, candidate_turn / 2.)
    if sum(map(abs, old)) > MAX_REFERENCE_WHEEL_RAD_S + 1e-9:
        raise Fault('remote_reference_state_outside_plan')
    base = [min(abs(o), abs(c)) for o, c in zip(old, candidate)]
    increases = [abs(c) - b for c, b in zip(candidate, base)]
    room = max(0., MAX_REFERENCE_WHEEL_RAD_S - sum(base))
    factor = min(1., room / sum(increases)) if sum(increases) else 1.
    result = [math.copysign(b + factor * inc, c)
              for b, inc, c in zip(base, increases, candidate)]
    return result[0] * radius, result[1] * 2.
