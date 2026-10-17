import io
import math
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from attitude import Fault
from self_righting_rate_recovery import PLAN,main
from self_righting_supervised import SupervisedRecovery
from self_righting_trial import recovery_signal


class RateRecoveryTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.,position=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,roll_deg=0.,
            pitch_error_deg=pitch,wheel_position_forward_rad={0:position,1:position})

    def controller_in_rise(self):
        c=SupervisedRecovery()
        for i in range(42):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        self.assertEqual(c.phase,'RISING')
        return c

    def test_inert_default_and_retired_launch_held_before_io(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertTrue(PLAN.get('motion_hold_reason'))
        errors=io.StringIO()
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stderr(errors),self.assertRaises(SystemExit):
            main(['--run-rate-reference-recovery'])
        self.assertIn('motion_trial_on_hold',errors.getvalue())

    def test_reference_is_bounded_symmetric_and_matches_balance_slope(self):
        for theta in (1e-4,18.,45.,90.):
            value,kd,target=recovery_signal(theta,-50.,PLAN)
            opposite,_,opposite_target=recovery_signal(-theta,50.,PLAN)
            self.assertLessEqual(abs(target),300.)
            self.assertAlmostEqual(opposite,-value)
            self.assertAlmostEqual(opposite_target,-target)
        theta=1e-4;rate=.01
        value,_,_=recovery_signal(theta,rate,PLAN)
        linear=PLAN['output_scale_nm']*(PLAN['ap_kp']*math.radians(theta)+PLAN['ap_kd']*math.radians(rate))
        self.assertAlmostEqual(value,linear,places=10)
        with self.assertRaisesRegex(Fault,'invalid_recovery_rate_reference'):
            recovery_signal(90.,0.,dict(PLAN,recovery_rate_max_dps=450.))

    def test_fading_rate_keeps_active_pose_control_in_new_profile(self):
        c=self.controller_in_rise()
        c(self.frame(.42,65.,-180.,.09),{0:9.,1:9.},PLAN)
        a=self.frame(.43,64.,-40.,.18);c(a,{0:9.,1:9.},PLAN)
        self.assertEqual(c.phase,'RISING');self.assertIsNone(c.abort_reason)
        self.assertLess(a['self_righting']['desired_body_pitch_rate_dps'],0.)
        for v in a['self_righting']['native_velocity_budget']['predicted_net_torque_nm'].values():
            self.assertLessEqual(abs(v),PLAN['predicted_net_torque_limit_nm'])

    def test_native_mode_normal_exit_preserves_last_target_not_zero_ff_estimate(self):
        c=self.controller_in_rise()
        c(self.frame(.42,65.,-180.,.09),{0:9.,1:9.},PLAN)
        old=c.velocity_targets.copy()
        c.start_abort('test_normal_exit',self.frame(.43,64.,-40.,.18),{0:9.,1:9.},PLAN)
        for mid in (0,1):self.assertAlmostEqual(c.abort_initial[mid],old[mid])

    def test_real_body_rate_fault_stays_immediate_and_latched(self):
        c=self.controller_in_rise()
        with self.assertRaisesRegex(Fault,'body_rotation_rate_stop'):
            c(self.frame(.42,65.,-410.,.09),{0:9.,1:9.},PLAN)
        with self.assertRaisesRegex(Fault,'fault_latched'):
            c(self.frame(.43),{0:0.,1:0.},PLAN)


if __name__=='__main__':unittest.main()
