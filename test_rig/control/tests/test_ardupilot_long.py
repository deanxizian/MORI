"""The requested longer repeat cannot silently widen motion or restart itself."""
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from ground_ardupilot_observe_long import LONG_PLAN,main
from ground_ardupilot_recovery import RECOVERY_PLAN
import test_ardupilot_balance as baseline


class LongerObservationTests(unittest.TestCase):
    def test_only_duration_and_labels_changed_and_default_is_inert(self):
        self.assertEqual({k for k in RECOVERY_PLAN if RECOVERY_PLAN[k]!=LONG_PLAN[k]},
                         {'name','duration_s','active_message'})
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_finite_sixty_seconds_stops_both_and_does_not_rearm(self):
        report=baseline.AdapterTests().run_case(plan=LONG_PLAN)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(60<=report['elapsed_s']<60.02)
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')


if __name__=='__main__':
    unittest.main()
