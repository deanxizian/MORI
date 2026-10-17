import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_fast_transfer import PLAN,main
from self_righting_travel_window import PLAN as REFERENCE
from self_righting_velocity_preparation_headroom import main as used_main
from self_righting_supervised import SupervisedRecovery


class FastTransferTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.,pos=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,pitch_error_deg=pitch,roll_deg=0.,
            wheel_position_forward_rad={0:pos,1:pos},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def prepare(self,plan):
        c=SupervisedRecovery()
        for i in range(41):c(self.frame(i*.01),{0:0.,1:0.},plan)
        return c

    def test_only_transfer_time_changes_and_torque_preparation_restored(self):
        keys={'name','active_message','motion_hold_reason','rise_ramp_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in REFERENCE.items() if k not in keys})
        self.assertEqual(PLAN['rise_ramp_s'],.04)
        self.assertFalse(PLAN['native_velocity_control'])
        self.assertNotIn('preparation_velocity_target_limit_rad_s',PLAN)

    def test_reversal_completes_earlier_with_same_net_budget(self):
        c=self.prepare(PLAN);old=self.prepare(REFERENCE)
        for i in range(1,6):
            a=self.frame(.4+i*.01,80.,-100.,i*.01)
            old_a=self.frame(.4+i*.01,80.,-100.,i*.01)
            c(a,{0:1.,1:1.},PLAN);old(old_a,{0:1.,1:1.},REFERENCE)
            self.assertLessEqual(abs(c.previous_net_common),.350000001)
        self.assertGreater(a['self_righting']['common_request_nm'],.34)
        self.assertLess(old_a['self_righting']['common_request_nm'],.15)

    def test_default_inert_and_used_entry_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-preparation-headroom','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
