import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_medium_transfer import PLAN,main
from self_righting_travel_window import PLAN as REFERENCE
from self_righting_fast_transfer import main as used_main
from self_righting_supervised import SupervisedRecovery


class MediumTransferTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.,pos=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,pitch_error_deg=pitch,roll_deg=0.,
            wheel_position_forward_rad={0:pos,1:pos},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def test_only_transfer_time_changes(self):
        keys={'name','active_message','motion_hold_reason','rise_ramp_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in REFERENCE.items() if k not in keys})
        self.assertEqual(PLAN['rise_ramp_s'],.06)
        self.assertFalse(PLAN['native_velocity_control'])

    def test_net_budget_and_intermediate_transfer(self):
        c=SupervisedRecovery();old=SupervisedRecovery()
        for i in range(41):
            c(self.frame(i*.01),{0:0.,1:0.},PLAN)
            old(self.frame(i*.01),{0:0.,1:0.},REFERENCE)
        for i in range(1,6):
            a=self.frame(.4+i*.01,80.,-100.,i*.01);b=self.frame(.4+i*.01,80.,-100.,i*.01)
            c(a,{0:1.,1:1.},PLAN);old(b,{0:1.,1:1.},REFERENCE)
            self.assertLessEqual(abs(c.previous_net_common),.350000001)
        self.assertGreater(a['self_righting']['common_request_nm'],.23)
        self.assertLess(b['self_righting']['common_request_nm'],.15)

    def test_default_inert_and_faulted_entry_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-fast-transfer','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
