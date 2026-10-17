import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from attitude import Fault
from self_righting_speed_window import PLAN,main
from self_righting_morning_supply import PLAN as REFERENCE
from self_righting_supervised import SupervisedRecovery
from self_righting_trial import govern_rise_speed


class SpeedWindowTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,
                    pitch_error_deg=pitch,roll_deg=0.,
                    wheel_position_forward_rad={0:0.,1:0.},
                    wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def rise(self,plan):
        c=SupervisedRecovery()
        for i in range(41):c(self.frame(i*.01),{0:0.,1:0.},plan)
        return c

    def test_extension_requires_explicit_boolean_and_retains_old_cap(self):
        for changes,reason in ((dict(allow_wheel_speed_extension=False),'invalid_rise_wheel_speed_limit'),
                               (dict(allow_wheel_speed_extension='yes'),'invalid_wheel_speed_extension'),
                               (dict(wheel_speed_limit_rad_s=16.51,rise_wheel_speed_limit_rad_s=16.51),'invalid_rise_wheel_speed_limit')):
            with self.assertRaisesRegex(Fault,reason):
                SupervisedRecovery().validate_arm(self.frame(.01),{0:0.,1:0.},dict(PLAN,**changes))
        SupervisedRecovery().validate_arm(self.frame(.01),{0:0.,1:0.},PLAN)

    def test_only_declared_speed_budgets_change(self):
        changed={'name','active_message','motion_hold_reason','allow_wheel_speed_extension',
                 'wheel_speed_limit_rad_s','rise_wheel_speed_limit_rad_s',
                 'rise_speed_target_rad_s','abort_speed_trigger_rad_s','abort_target_limit_rad_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in changed},
                         {k:v for k,v in REFERENCE.items() if k not in changed})
        self.assertLess(PLAN['rise_speed_target_rad_s'],PLAN['abort_speed_trigger_rad_s'])
        self.assertLess(PLAN['abort_target_limit_rad_s'],PLAN['wheel_speed_limit_rad_s'])

    def test_new_and_old_feedback_stops_remain_profile_specific_and_latch(self):
        new=self.rise(PLAN)
        new(self.frame(.41,70.,-100.),{0:16.,1:16.},PLAN)
        self.assertEqual(new.phase,'ABORT_BRAKE')
        with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
            new(self.frame(.42,70.,-100.),{0:16.6,1:16.6},PLAN)
        with self.assertRaisesRegex(Fault,'fault_latched'):
            new(self.frame(.43),{0:0.,1:0.},PLAN)
        old=self.rise(REFERENCE)
        with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
            old(self.frame(.41,70.,-100.),{0:16.,1:16.},REFERENCE)

    def test_soft_envelope_brakes_before_feedback_stop(self):
        request=govern_rise_speed({0:.35,1:.35},{0:16.,1:16.},PLAN,0.,{0:16.,1:16.})
        self.assertTrue(all(v<0 for v in request.values()))

    def test_default_has_no_file_or_motor_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)


if __name__=='__main__':unittest.main()
