import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from attitude import Fault
from self_righting_preroll_early import PLAN,main
from self_righting_travel_window import PLAN as RETIRED,main as retired_main
from self_righting_supervised import SupervisedRecovery


class EarlierPrerollTests(unittest.TestCase):
    def frame(self,t,pitch=90.,pos=None):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=0.,
            pitch_error_deg=pitch,roll_deg=0.,
            wheel_position_forward_rad=pos or {0:0.,1:0.},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def prepare(self,plan):
        c=SupervisedRecovery()
        for i in range(10):c(self.frame(i*.01),{0:0.,1:0.},plan)
        return c

    def test_only_preparation_target_changes(self):
        keys={'name','active_message','motion_hold_reason','pre_roll_target_rad_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in RETIRED.items() if k not in keys})
        self.assertEqual(PLAN['pre_roll_target_rad_s'],8.)

    def test_reversal_gate_is_earlier_with_coherent_timed_positions(self):
        pos={0:-.081,1:-.07};v={0:-8.1,1:-7.}
        c=self.prepare(PLAN);old=self.prepare(RETIRED)
        c(self.frame(.10,pos=pos),v,PLAN)
        old(self.frame(.10,pos=pos),v,RETIRED)
        self.assertEqual(c.phase,'RISING');self.assertEqual(old.phase,'PRE_ROLL')
        self.assertEqual(c.pre_roll_exit,'speed_target')

    def test_wrong_way_guard_still_latches(self):
        c=self.prepare(PLAN);pos={0:-.081,1:-.07};v={0:-8.1,1:-7.}
        c(self.frame(.10,pos=pos),v,PLAN)
        with self.assertRaisesRegex(Fault,'self_righting_wrong_way'):
            c(self.frame(.11,96.,pos),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'fault_latched'):
            c(self.frame(.12,90.,pos),{0:0.,1:0.},PLAN)

    def test_default_inert_and_used_launch_rejected_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                retired_main(['--run-travel-window','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
