import unittest
from attitude import PitchEstimator,Fault
from test_attitude_air import CAL


class RotatingLowGTests(unittest.TestCase):
    def sample(self,t,g=1.,rate=0.):
        return dict(t_read_complete=t,accel_g=[0.,0.,g],gyro_dps=[0.,-rate,0.])

    def estimator(self):
        e=PitchEstimator(CAL,fuse_roll=True);e.update(self.sample(0.));return e

    def test_low_g_is_still_rejected_without_explicit_opt_in(self):
        with self.assertRaisesRegex(Fault,'acceleration_outside_dynamic_window'):
            self.estimator().update(self.sample(.01,.16,160.),dynamic=True)

    def test_short_rotating_frame_is_gyro_only(self):
        a=self.estimator().update(self.sample(.01,.16,160.),dynamic=True,allow_rotating_low_g=True)
        self.assertTrue(a['rotating_low_g_transient'])
        self.assertEqual(a['gravity_correction_weight'],0.)
        self.assertNotEqual(a['pitch_deg'],a['pitch_accel_deg'])

    def test_stationary_low_g_and_extreme_values_reject_immediately(self):
        for g,rate in ((.16,0.),(.16,99.),(.01,160.),(3.,160.)):
            with self.subTest(g=g,rate=rate),self.assertRaisesRegex(Fault,'acceleration_outside_dynamic_window'):
                self.estimator().update(self.sample(.01,g,rate),dynamic=True,allow_rotating_low_g=True)

    def test_rotating_low_g_is_time_bounded(self):
        e=self.estimator()
        for t in (.01,.02):e.update(self.sample(t,.16,160.),dynamic=True,allow_rotating_low_g=True)
        with self.assertRaisesRegex(Fault,'sustained_rotating_low_g'):
            e.update(self.sample(.031,.16,160.),dynamic=True,allow_rotating_low_g=True)

    def test_recovery_clears_short_event_and_original_sustained_guard_remains(self):
        e=self.estimator();e.update(self.sample(.01,.16,160.),dynamic=True,allow_rotating_low_g=True)
        a=e.update(self.sample(.02,1.,160.),dynamic=True,allow_rotating_low_g=True)
        self.assertFalse(a['rotating_low_g_transient'])
        for t in (.03,.04,.05,.06,.07):e.update(self.sample(t,.3,160.),dynamic=True,allow_rotating_low_g=True)
        with self.assertRaisesRegex(Fault,'sustained_dynamic_acceleration'):
            e.update(self.sample(.081,.3,160.),dynamic=True,allow_rotating_low_g=True)

    def test_recent_rotation_covers_deceleration_but_is_opt_in(self):
        e=self.estimator();e.update(self.sample(.01,1.,160.),dynamic=True,allow_rotating_low_g=True)
        with self.assertRaisesRegex(Fault,'acceleration_outside_dynamic_window'):
            e.update(self.sample(.02,.1,25.),dynamic=True,allow_rotating_low_g=True)
        e=self.estimator();e.update(self.sample(.01,1.,160.),dynamic=True,allow_rotating_low_g=True)
        a=e.update(self.sample(.02,.1,25.),dynamic=True,allow_rotating_low_g=True,rotating_low_g_history_s=.02)
        self.assertTrue(a['rotating_low_g_recent_context']);self.assertEqual(a['gravity_correction_weight'],0.)

    def test_recent_context_expires_and_cannot_start_from_static_low_g(self):
        e=self.estimator()
        with self.assertRaisesRegex(Fault,'acceleration_outside_dynamic_window'):
            e.update(self.sample(.01,.1,25.),dynamic=True,allow_rotating_low_g=True,rotating_low_g_history_s=.02)
        e=self.estimator();e.update(self.sample(.01,1.,160.),dynamic=True,allow_rotating_low_g=True)
        e.update(self.sample(.02,.1,25.),dynamic=True,allow_rotating_low_g=True,rotating_low_g_history_s=.02)
        with self.assertRaisesRegex(Fault,'acceleration_outside_dynamic_window'):
            e.update(self.sample(.031,.1,25.),dynamic=True,allow_rotating_low_g=True,rotating_low_g_history_s=.02)

    def test_history_does_not_relax_extreme_g_or_static_reset(self):
        for g in (.01,3.):
            e=self.estimator();e.update(self.sample(.01,1.,160.),dynamic=True,allow_rotating_low_g=True)
            with self.assertRaisesRegex(Fault,'acceleration_outside_dynamic_window'):
                e.update(self.sample(.02,g,25.),dynamic=True,allow_rotating_low_g=True,rotating_low_g_history_s=.02)
        e=self.estimator();e.update(self.sample(.01,1.,160.),dynamic=True,allow_rotating_low_g=True)
        e.update(self.sample(.02))
        with self.assertRaisesRegex(Fault,'acceleration_outside_dynamic_window'):
            e.update(self.sample(.03,.1,25.),dynamic=True,allow_rotating_low_g=True,rotating_low_g_history_s=.02)
        with self.assertRaisesRegex(Fault,'invalid_rotating_low_g_history'):
            self.estimator().update(self.sample(.01),dynamic=True,allow_rotating_low_g=True,rotating_low_g_history_s=.03)

if __name__=='__main__':unittest.main()

