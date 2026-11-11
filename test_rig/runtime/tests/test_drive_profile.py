import math
import unittest
from attitude import Fault
from drive_profile import ResponsiveDriveProfile
from two_deck_remote_drive import DriveVelocityProfile


class DriveProfileTests(unittest.TestCase):
    def time_to_90_percent(self, cls, sign):
        profile = cls()
        for i in range(1000):
            if sign * profile.update(sign * .12, .005) >= .108:
                return (i + 1) * .005
        self.fail('target never reached')

    def test_forward_reverse_both_faster_with_same_target(self):
        for sign in (-1, 1):
            self.assertLess(self.time_to_90_percent(ResponsiveDriveProfile, sign),
                            .7 * self.time_to_90_percent(DriveVelocityProfile, sign))

    def test_release_uses_original_braking_from_identical_state(self):
        for sign in (-1, 1):
            new, old = ResponsiveDriveProfile(), DriveVelocityProfile()
            for _ in range(30):new.update(sign * .12, .005)
            old.lead, old.velocity = new.lead, new.velocity
            for _ in range(700):
                self.assertEqual(new.update(0, .005), old.update(0, .005))
            self.assertEqual(new.velocity, 0.)

    def test_taps_opposing_commands_disconnect_are_bounded_and_symmetric(self):
        positive, negative = ResponsiveDriveProfile(), ResponsiveDriveProfile()
        targets = [.16] * 20 + [0.] * 10 + [-.16] * 400 + [.16] * 400 + [0.] * 700
        before = 0.
        for target in targets:
            v = positive.update(target, .005)
            self.assertAlmostEqual(v, -negative.update(-target, .005))
            self.assertLessEqual(abs(v), .16 + 1e-12)
            self.assertLessEqual(abs(v - before), .40 * .005 + 1e-12)
            before = v
        self.assertEqual(before, 0.)

    def test_invalid_inputs_still_rejected(self):
        for target, dt in ((.17, .005), (math.nan, .005), (.12, .026), (.12, 0.)):
            with self.assertRaises(Fault):ResponsiveDriveProfile().update(target, dt)
