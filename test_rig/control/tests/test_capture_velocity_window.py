import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from attitude import Fault
from self_righting_capture_velocity_window import PLAN,main
from self_righting_governor_response import PLAN as OLD,main as used_main
from self_righting_supervised import SupervisedRecovery


class CaptureVelocityWindowTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.,pos=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,pitch_error_deg=pitch,roll_deg=0.,
            wheel_position_forward_rad={0:pos,1:pos},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def rise(self,plan):
        c=SupervisedRecovery()
        for i in range(41):c(self.frame(i*.01),{0:0.,1:0.},plan)
        return c

    def test_only_capture_speed_gate_changes_stability_unchanged(self):
        keys={'name','active_message','motion_hold_reason','capture_velocity_m_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in OLD.items() if k not in keys})
        self.assertEqual(PLAN['capture_velocity_m_s'],.6)
        self.assertEqual(PLAN['stable_duration_s'],30.)
        self.assertEqual(PLAN['stable_pitch_deg'],3.)
        self.assertEqual(PLAN['stable_velocity_m_s'],.03)

    def test_058_velocity_can_capture_but_not_claim_stability(self):
        c=self.rise(PLAN);old=self.rise(OLD)
        c(self.frame(.41,17.8,-28.,.15),{0:15.,1:15.},PLAN)
        old(self.frame(.41,17.8,-28.,.15),{0:15.,1:15.},OLD)
        self.assertEqual(c.phase,'CAPTURE');self.assertEqual(old.phase,'RISING')
        with self.assertRaisesRegex(Fault,'stable_window_not_met'):c.finish()

    def test_other_capture_gates_still_reject(self):
        for pitch,rate,speed in ((18.1,-28.,15.),(17.8,-121.,15.),(17.8,-28.,15.7)):
            c=self.rise(PLAN)
            c(self.frame(.41,pitch,rate,speed*.01),{0:speed,1:speed},PLAN)
            self.assertEqual(c.phase,'RISING')

    def test_default_inert_and_used_entry_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-governor-response','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
