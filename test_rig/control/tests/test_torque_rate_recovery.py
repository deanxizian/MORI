import io
import math
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_torque_recovery import PLAN as PREVIOUS
from self_righting_charged_supply import PLAN,main
from self_righting_supervised import SupervisedRecovery
from protocol import RATIO

class TorqueRateRecoveryTests(unittest.TestCase):
    def test_adapter_comparison_preserves_body_reference_and_hard_limits(self):
        for k in ('predicted_net_torque_limit_nm','estimated_torque_limit_nm','wheel_speed_limit_rad_s',
                  'rise_wheel_speed_limit_rad_s','pitch_rate_limit_dps',
                  'temperature_limit_c','recovery_settle_time_s',
                  'recovery_rate_gain_nm_per_rad_s','recovery_gravity_ff_nm'):
            self.assertEqual(PLAN[k],PREVIOUS[k],k)
        self.assertFalse(PLAN['native_velocity_control'])
        self.assertTrue(PLAN['rise_compensate_native_damping'])
        self.assertLess(PLAN['rise_native_wheel_damping_nm_per_rad_s'],PREVIOUS['rise_native_wheel_damping_nm_per_rad_s'])
        for k in ('native_wheel_damping_nm_per_rad_s','pre_roll_native_wheel_damping_nm_per_rad_s'):
            self.assertEqual(PLAN[k],PREVIOUS[k])

    def test_inert_default_and_charge_hold_rejects_before_io(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        errors=io.StringIO()
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stderr(errors),self.assertRaises(SystemExit):
            main(['--run-charged-supply-recovery'])
        self.assertIn('motion_trial_on_hold',errors.getvalue())

    def test_feedforward_packet_budget_keeps_net_limit_during_finite_rise(self):
        c=SupervisedRecovery()
        def f(t,pitch=90.,rate=0.,position=0.):
            return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,roll_deg=0.,
                pitch_error_deg=pitch,wheel_position_forward_rad={0:position,1:position},
                wheel_feedback_received_monotonic={0:t-.002,1:t-.001})
        for i in range(44):
            a=f(i*.01);commands=c(a,{0:0.,1:0.},PLAN);p=c.motor_plan(PLAN)
            self.assertFalse(p.get('native_velocity_control'))
            step=RATIO**2/128000000;kd=math.floor(p['native_wheel_damping_nm_per_rad_s']/step)*step
            for mid in (0,1):
                self.assertLessEqual(abs(commands[mid]),p['feedforward_torque_limit_nm'])
                self.assertLessEqual(abs(commands[mid]-kd*0.),PLAN['predicted_net_torque_limit_nm'])
        a=f(.44,65.,-180.,.09);commands=c(a,{0:9.,1:9.},PLAN);p=c.motor_plan(PLAN)
        kd=math.floor(p['native_wheel_damping_nm_per_rad_s']/step)*step
        for mid in (0,1):self.assertLessEqual(abs(commands[mid]-kd*9.),PLAN['predicted_net_torque_limit_nm'])
        self.assertEqual(c.phase,'RISING')

if __name__=='__main__':unittest.main()
