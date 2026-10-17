import unittest
from attitude import Fault
from self_righting_trial import recovery_signal
from self_righting_feedback_time import PLAN as OLD
from self_righting_mid_lift import PLAN

class MidLiftTests(unittest.TestCase):
    def test_added_term_is_middle_only_symmetric_and_cap_is_unchanged(self):
        for k in ('control_torque_limit_nm','predicted_net_torque_limit_nm','estimated_torque_limit_nm',
                  'wheel_speed_limit_rad_s','rise_pitch_rate_limit_dps','temperature_limit_c','recovery_rate_max_dps'):
            self.assertEqual(PLAN[k],OLD[k])
        for theta in (0.,.001,10.,15.,75.,80.,90.):
            self.assertEqual(recovery_signal(theta,-200.,PLAN),recovery_signal(theta,-200.,OLD))
        for theta in (20.,30.,50.,70.):
            new,_,_=recovery_signal(theta,-250.,PLAN);old,_,_=recovery_signal(theta,-250.,OLD)
            self.assertGreater(new,old)
            self.assertAlmostEqual(recovery_signal(-theta,250.,PLAN)[0],-new)
            self.assertLessEqual(new-old,.17)

    def test_invalid_mid_range_and_excessive_feedforward_reject(self):
        for changes in (dict(recovery_mid_gravity_ff_nm=.36),dict(recovery_mid_inner_deg=30.),dict(recovery_mid_outer_deg=90.)):
            with self.assertRaisesRegex(Fault,'invalid_mid_recovery_feedforward'):
                recovery_signal(60.,-250.,dict(PLAN,**changes))

if __name__=='__main__':unittest.main()
