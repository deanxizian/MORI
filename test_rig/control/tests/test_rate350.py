import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from attitude import Fault
from self_righting_rate350 import PLAN,main
from self_righting_morning_supply import PLAN as REFERENCE
from self_righting_supervised import SupervisedRecovery
from self_righting_trial import recovery_signal


class Rate350Tests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,
                    pitch_error_deg=pitch,roll_deg=0.,
                    wheel_position_forward_rad={0:0.,1:0.},
                    wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def test_only_soft_far_reference_changes(self):
        changed={'name','active_message','motion_hold_reason','recovery_rate_max_dps'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in changed},
                         {k:v for k,v in REFERENCE.items() if k not in changed})
        self.assertEqual(PLAN['recovery_rate_max_dps'],350.)

    def test_far_request_lower_but_near_upright_law_preserved(self):
        self.assertLess(recovery_signal(75.,-350.,PLAN)[0],
                        recovery_signal(75.,-350.,REFERENCE)[0])
        for pitch in (0.,18.,30.,40.,50.):
            self.assertEqual(recovery_signal(pitch,-100.,PLAN),
                             recovery_signal(pitch,-100.,REFERENCE))

    def test_soft_reference_does_not_replace_original_hard_stops(self):
        for excessive,reason in ((-501.,'body_rotation_rate_stop'),(401.,'body_outward_rotation_rate_stop')):
            c=SupervisedRecovery()
            for i in range(41):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
            c(self.frame(.41,65.,-450.),{0:0.,1:0.},PLAN)
            with self.assertRaisesRegex(Fault,reason):
                c(self.frame(.42,65.,excessive),{0:0.,1:0.},PLAN)
            with self.assertRaisesRegex(Fault,'fault_latched'):
                c(self.frame(.43),{0:0.,1:0.},PLAN)

    def test_default_has_no_file_or_motor_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)


if __name__=='__main__':raise SystemExit(unittest.main())
