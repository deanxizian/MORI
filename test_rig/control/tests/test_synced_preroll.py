import unittest
from self_righting_preroll_momentum import PLAN
from self_righting_supervised import SupervisedRecovery

class SyncedPrerollTests(unittest.TestCase):
    def frame(self,t):
        return dict(t=t,dt=.01,pitch_deg=90.,pitch_rate_dps=0.,roll_deg=0.,pitch_error_deg=90.,
            wheel_position_forward_rad={0:0.,1:0.},wheel_feedback_received_monotonic={0:t-.002,1:t-.001})
    def test_fast_wheel_alone_does_not_end_preparation(self):
        c=SupervisedRecovery()
        for i in range(20):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        c(self.frame(.20),{0:-13.,1:-11.},PLAN);self.assertEqual(c.phase,'PRE_ROLL')
        c(self.frame(.21),{0:-13.,1:-13.},PLAN);self.assertEqual(c.phase,'RISING')
        self.assertEqual(c.pre_roll_exit,'speed_target')
    def test_preparation_remains_finite_without_both_wheels_reaching_target(self):
        c=SupervisedRecovery()
        for i in range(42):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        self.assertEqual(c.phase,'RISING');self.assertEqual(c.pre_roll_exit,'time_limit')
        self.assertEqual(PLAN['pre_roll_duration_s'],.4)
        self.assertLess(PLAN['pre_roll_speed_limit_rad_s'],PLAN['wheel_speed_limit_rad_s'])

    def test_reverse_preload_not_misclassified_as_lift_speed_headroom(self):
        c=SupervisedRecovery()
        for i in range(20):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        c(self.frame(.20),{0:-13.,1:-13.},PLAN);self.assertEqual(c.phase,'RISING')
        c(self.frame(.21),{0:-14.1,1:-14.1},PLAN)
        self.assertEqual(c.phase,'RISING');self.assertIsNone(c.abort_reason)
        c(self.frame(.22),{0:14.1,1:14.1},PLAN)
        self.assertEqual(c.phase,'ABORT_BRAKE')
        self.assertEqual(c.abort_reason,'wheel_headroom_low_before_capture')

if __name__=='__main__':unittest.main()

