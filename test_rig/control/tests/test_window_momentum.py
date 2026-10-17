import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from attitude import Fault
from self_righting_window_momentum import PLAN,main
from self_righting_morning_supply import PLAN as REFERENCE
from self_righting_supervised import SupervisedRecovery
from self_righting_trial import recovery_signal


class WindowMomentumTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,
                    pitch_error_deg=pitch,roll_deg=0.,
                    wheel_position_forward_rad={0:0.,1:0.},
                    wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def test_only_far_reference_changes_not_actuator_or_hard_guard_settings(self):
        changed={'name','active_message','motion_hold_reason','recovery_rate_max_dps'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in changed},
                         {k:v for k,v in REFERENCE.items() if k not in changed})
        self.assertEqual(PLAN['recovery_rate_max_dps'],450.)
        self.assertLess(PLAN['recovery_rate_max_dps'],PLAN['rise_pitch_rate_limit_dps'])

    def test_far_request_increases_but_near_capture_behavior_is_unchanged(self):
        old=recovery_signal(75.,-400.,REFERENCE)
        new=recovery_signal(75.,-400.,PLAN)
        self.assertGreater(new[0],old[0])
        self.assertEqual(new[2],-450.)
        for pitch in (0.,18.,30.,40.,60.):
            self.assertEqual(recovery_signal(pitch,-100.,PLAN),
                             recovery_signal(pitch,-100.,REFERENCE))

    def test_default_has_no_file_or_motor_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_original_inward_and_outward_faults_still_latch(self):
        for rate,reason in ((-501.,'body_rotation_rate_stop'),(401.,'body_outward_rotation_rate_stop')):
            c=SupervisedRecovery()
            for i in range(41):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
            with self.assertRaisesRegex(Fault,reason):
                c(self.frame(.41,70.,rate),{0:0.,1:0.},PLAN)
            with self.assertRaisesRegex(Fault,'fault_latched'):
                c(self.frame(.42),{0:0.,1:0.},PLAN)


if __name__=='__main__':unittest.main()
