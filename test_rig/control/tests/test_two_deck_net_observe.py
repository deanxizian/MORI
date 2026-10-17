import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from two_deck_net_observe import PLAN,main
from two_deck_net_torque import PLAN as BASE


class ObserveTests(unittest.TestCase):
    def test_only_observation_duration_changes_and_default_has_no_io(self):
        self.assertEqual({k for k in PLAN if PLAN[k]!=BASE[k]},
                         {'name','duration_s','active_message'})
        self.assertEqual(PLAN['duration_s'],30.)
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)


if __name__=='__main__':unittest.main()
