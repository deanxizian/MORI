import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_travel_window import PLAN,main
from self_righting_speed_window import PLAN as RETIRED,main as retired_main
from self_righting_supervised import SupervisedRecovery


class TravelWindowTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.,travel=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,
            pitch_error_deg=pitch,roll_deg=0.,
            wheel_position_forward_rad={0:travel/.04,1:travel/.04},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def test_only_early_exit_changes_and_hard_guard_stays(self):
        meta={'name','active_message','motion_hold_reason','abort_net_reserve_trigger_m'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in meta},
                         {k:v for k,v in RETIRED.items() if k not in meta})
        self.assertEqual(PLAN['abort_net_reserve_trigger_m'],.15)
        self.assertTrue(RETIRED['motion_hold_reason'])
        self.assertEqual(PLAN['net_rolling_limit_m'],.30)
        self.assertEqual(PLAN['rolling_path_limit_m'],1.)

    def test_new_reserve_preserves_rising_then_enters_normal_exit(self):
        c=SupervisedRecovery()
        for i in range(41):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        # Coherent position/time input for gate testing, not a plant simulation.
        for i in range(1,26):
            c(self.frame(.40+i*.01,20.,-62.,i*.0056),{0:14.,1:14.},PLAN)
            self.assertEqual(c.phase,'RISING')
        for i in (26,27):
            c(self.frame(.40+i*.01,20.,-62.,i*.0056),{0:14.,1:14.},PLAN)
        self.assertEqual(c.phase,'ABORT_BRAKE')
        self.assertEqual(c.abort_reason,'travel_reserve_for_normal_exit')

    def test_default_inert_and_retired_entry_rejected_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                retired_main(['--run-speed-window','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
