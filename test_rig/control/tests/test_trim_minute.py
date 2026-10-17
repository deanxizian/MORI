from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from attitude import Fault
from ground_hold_trial import HoldTravel
from two_deck_trim_minute import PLAN, main
from two_deck_trim_observe import PLAN as BASE


class TrimMinuteTests(unittest.TestCase):
    def travel(self):
        return HoldTravel({0: {'position_rad': 0.}, 1: {'position_rad': 0.}},
                          {0: 1, 1: -1}, PLAN)

    def pair(self, travel, distance):
        for mid, sign in ((0, 1), (1, -1)):
            travel.update(mid, {'position_rad': sign * distance /
                               PLAN['nominal_wheel_radius_m']})

    def test_no_default_motion_and_only_cumulative_window_changes(self):
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('I/O')), \
             patch('air_trial.run', side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(main([]), 0)
        changes = {k for k in set(PLAN) | set(BASE) if PLAN.get(k) != BASE.get(k)}
        self.assertEqual(changes, {'name', 'control_phase', 'active_message',
                                  'rolling_path_limit_m'})

    def test_reversals_do_not_reset_two_metre_cumulative_stop(self):
        travel = self.travel()
        for _ in range(99):
            self.pair(travel, .01)
            self.pair(travel, 0.)
        self.pair(travel, .015)
        self.assertTrue(all(1.99 < p < 2. for p in travel.path.values()))
        with self.assertRaisesRegex(Fault, 'wheel_rolling_path_stop'):
            self.pair(travel, 0.)

    def test_net_displacement_still_stops_at_original_thirty_cm(self):
        travel = self.travel()
        with self.assertRaisesRegex(Fault, 'wheel_net_travel_stop'):
            for i in range(1, 32):
                self.pair(travel, i * .01)
        self.assertLess(max(travel.path.values()), .32)

    def test_single_wheel_divergence_still_stops_at_three_cm(self):
        travel = self.travel()
        with self.assertRaisesRegex(Fault, 'differential_wheel_travel_stop'):
            travel.update(0, {'position_rad': .031 / PLAN['nominal_wheel_radius_m']})


if __name__ == '__main__':
    unittest.main()
