import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch
from air_trial import PORT
from attitude import Fault
from self_righting_headroom_window import PLAN,main
from self_righting_inward_momentum import PLAN as REFERENCE
from self_righting_supervised import SupervisedRecovery
from self_righting_trial import govern_rise_speed


class HeadroomWindowTests(unittest.TestCase):
    def test_overnight_hold_rejects_even_complete_launch_flags_before_io(self):
        args=['--run-headroom-window','--operator-ready','--ack-query-timeout',
              '--port',PORT,'--calibration','not-opened.json','--output','not-created.json']
        errors=io.StringIO()
        with patch('air_trial.sys.platform','linux'), \
             patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stderr(errors),self.assertRaises(SystemExit):
            main(args)
        self.assertIn('motion_trial_on_hold',errors.getvalue())

    def frame(self,t,pitch=90.,rate=0.,position=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,
                    roll_deg=0.,pitch_error_deg=pitch,
                    wheel_position_forward_rad={0:position,1:position},
                    wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def rise(self):
        c=SupervisedRecovery()
        for i in range(41):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        self.assertEqual(c.phase,'RISING')
        return c

    def test_only_normal_speed_window_changes(self):
        changes={'name','active_message','motion_hold_reason','rise_speed_target_rad_s',
                 'abort_speed_trigger_rad_s','abort_target_limit_rad_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in changes},
                         {k:v for k,v in REFERENCE.items() if k not in changes})
        self.assertLess(PLAN['rise_speed_target_rad_s'],PLAN['abort_speed_trigger_rad_s'])
        self.assertLess(PLAN['abort_speed_trigger_rad_s'],PLAN['abort_target_limit_rad_s'])
        self.assertLess(PLAN['abort_target_limit_rad_s'],PLAN['wheel_speed_limit_rad_s'])

    def test_inward_progress_at_old_exit_speed_can_continue_but_new_exit_still_triggers(self):
        c=self.rise()
        c(self.frame(.41,45.,-80.,.141),{0:14.1,1:14.1},PLAN)
        self.assertIsNone(c.abort_reason)
        self.assertEqual(c.phase,'RISING')
        c(self.frame(.42,44.,-80.,.290),{0:14.9,1:14.9},PLAN)
        self.assertEqual(c.abort_reason,'wheel_headroom_low_before_capture')
        self.assertEqual(c.phase,'ABORT_BRAKE')
        self.assertLessEqual(max(map(abs,c.abort_targets.values())),15.)

    def test_soft_envelope_requests_braking_before_hard_limit(self):
        out=govern_rise_speed({0:.35,1:.35},{0:14.8,1:14.8},PLAN,0.,{0:14.8,1:14.8})
        self.assertTrue(all(v<0 for v in out.values()))

    def test_original_hard_speed_fault_latches(self):
        c=self.rise()
        with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
            c(self.frame(.41,45.,-80.,.156),{0:15.6,1:15.6},PLAN)
        with self.assertRaisesRegex(Fault,'fault_latched'):
            c(self.frame(.42),{0:0.,1:0.},PLAN)


if __name__=='__main__':unittest.main()
