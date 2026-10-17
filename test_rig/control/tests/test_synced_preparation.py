import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_synced_preparation import PLAN,main
from self_righting_preroll_early import main as used_main
from self_righting_travel_window import PLAN as REFERENCE
from self_righting_supervised import SupervisedRecovery


class SyncedPreparationTests(unittest.TestCase):
    def frame(self,t,pos=None):
        return dict(t=t,dt=.01,pitch_deg=90.,pitch_rate_dps=0.,pitch_error_deg=90.,roll_deg=0.,
            wheel_position_forward_rad=pos or {0:0.,1:0.},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def prepare(self,plan):
        c=SupervisedRecovery()
        for i in range(10):c(self.frame(i*.01),{0:0.,1:0.},plan)
        return c

    def test_restores_original_target_and_only_changes_both_gate(self):
        keys={'name','active_message','motion_hold_reason','pre_roll_target_both_wheels'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in REFERENCE.items() if k not in keys})
        self.assertEqual(PLAN['pre_roll_target_rad_s'],9.5)
        self.assertTrue(PLAN['pre_roll_target_both_wheels'])
        self.assertEqual(PLAN['pre_roll_speed_limit_rad_s'],13.)
        self.assertEqual(PLAN['pre_roll_duration_s'],.4)

    def test_one_wheel_does_not_end_preparation_but_both_do(self):
        c=self.prepare(PLAN);old=self.prepare(REFERENCE)
        a=self.frame(.10,{0:-.10,1:-.09});v={0:-10.,1:-9.}
        c(a,v,PLAN);old(self.frame(.10,{0:-.10,1:-.09}),v,REFERENCE)
        self.assertEqual(c.phase,'PRE_ROLL');self.assertEqual(old.phase,'RISING')
        c(self.frame(.11,{0:-.203,1:-.187}),{0:-10.3,1:-9.7},PLAN)
        self.assertEqual(c.phase,'RISING');self.assertEqual(c.pre_roll_exit,'speed_target')

    def test_default_inert_and_used_launch_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-early-preroll','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
