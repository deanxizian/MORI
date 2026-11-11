# SPDX-License-Identifier: GPL-3.0-or-later
"""Quicker forward/reverse acceleration with bounded acceleration and original release braking."""
import math
from attitude import Fault, clip, finite
from two_deck_remote_drive import DriveVelocityProfile
from motion_limits import MAX_DRIVE_M_S, DRIVE_ACCEL_M_S2


class ResponsiveDriveProfile(DriveVelocityProfile):
    def update(self, target, dt):
        finite(target, dt)
        if abs(target) > MAX_DRIVE_M_S + 1e-12 or not 0 < dt <= .025:
            raise Fault('remote_profile_outside_plan')
        accelerating = (target * self.velocity >= 0 and target * self.lead >= 0
                        and abs(target) > abs(self.velocity) + 1e-6)
        tau = .08 if accelerating else .20
        decay = math.exp(-dt / tau)
        old_lead = self.lead
        self.lead = target + (old_lead - target) * decay
        proposed = target + (self.velocity - target + (old_lead - target) * dt / tau) * decay
        self.velocity += clip(proposed - self.velocity, (DRIVE_ACCEL_M_S2 if accelerating else .30) * dt)
        if target == 0. and max(abs(self.lead), abs(self.velocity)) < .0001:
            self.lead = self.velocity = 0.
        return self.velocity
