import unittest
from attitude import Fault
from self_righting_inward_momentum import PLAN
from self_righting_supervised import SupervisedRecovery
from self_righting_trial import recovery_signal

class InwardMomentumTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,roll_deg=0.,pitch_error_deg=pitch,
                    wheel_position_forward_rad={0:0.,1:0.},wheel_feedback_received_monotonic={0:t-.002,1:t-.001})
    def rise(self):
        c=SupervisedRecovery()
        for i in range(42):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        return c
    def test_reference_is_below_inward_hard_stop(self):
        self.assertEqual(abs(recovery_signal(90.,0.,PLAN)[2]),400.)
        self.assertLess(PLAN['recovery_rate_max_dps'],PLAN['rise_pitch_rate_limit_dps'])
        self.assertEqual(PLAN['rise_outward_pitch_rate_limit_dps'],400.)
        c=self.rise();c(self.frame(.42,65.,-450.),{0:0.,1:0.},PLAN)
        self.assertEqual(c.phase,'RISING')
    def test_excessive_inward_and_original_outward_rates_latch_without_rearm(self):
        for rate,reason in ((-501.,'body_rotation_rate_stop'),(401.,'body_outward_rotation_rate_stop')):
            c=self.rise()
            with self.assertRaisesRegex(Fault,reason):c(self.frame(.42,65.,rate),{0:0.,1:0.},PLAN)
            with self.assertRaisesRegex(Fault,'fault_latched'):c(self.frame(.43),{0:0.,1:0.},PLAN)
    def test_outward_guard_also_applies_during_normal_abort(self):
        c=self.rise();c.start_abort('test',self.frame(.42,65.),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'body_outward_rotation_rate_stop'):
            c(self.frame(.43,66.,401.),{0:0.,1:0.},PLAN)

    def test_extension_requires_explicit_opt_in_and_separate_outward_guard(self):
        for changes,reason in ((dict(allow_inward_rate_extension=False),'invalid_rise_rate_limit'),
                               (dict(rise_outward_pitch_rate_limit_dps=450.),'outward_rate_guard_required')):
            with self.assertRaisesRegex(Fault,reason):
                SupervisedRecovery().validate_arm(self.frame(.01),{0:0.,1:0.},dict(PLAN,**changes))

if __name__=='__main__':unittest.main()

