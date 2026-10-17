import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_velocity_preparation_headroom import PLAN,main
from self_righting_velocity_preparation import PLAN as OLD,VelocityPreparation,main as used_main


class PreparationHeadroomTests(unittest.TestCase):
    def frame(self,t,pos=None):
        return dict(t=t,dt=.01,pitch_deg=90.,pitch_rate_dps=0.,pitch_error_deg=90.,roll_deg=0.,
            wheel_position_forward_rad=pos or {0:0.,1:0.},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def test_only_target_cap_changes_with_original_guards(self):
        meta={'name','active_message','motion_hold_reason','preparation_velocity_target_limit_rad_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in meta},
                         {k:v for k,v in OLD.items() if k not in meta})
        self.assertEqual(PLAN['preparation_velocity_target_limit_rad_s'],11.)
        self.assertEqual(PLAN['pre_roll_target_rad_s'],9.5)
        self.assertEqual(PLAN['pre_roll_speed_limit_rad_s'],13.)
        self.assertEqual(PLAN['predicted_net_torque_limit_nm'],.35)

    def test_targets_and_net_budget_remain_bounded(self):
        c=VelocityPreparation();pos=0.;v=0.
        for i in range(20):
            v=-min(8.8,i*.5);pos+=v*.01
            c(self.frame(i*.01,{0:pos,1:pos}),{0:v,1:v},PLAN)
            self.assertTrue(all(abs(x)<=11. for x in c.preparation_targets.values()))
            self.assertLessEqual(abs(c.previous_net_common),.35)
        self.assertTrue(any(abs(x)>10. for x in c.preparation_targets.values()))
        self.assertEqual(c.phase,'PRE_ROLL')
        self.assertEqual(c.motor_plan(PLAN)['wheel_speed_limit_rad_s'],13.)

    def test_default_inert_and_old_launch_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-velocity-preparation','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
