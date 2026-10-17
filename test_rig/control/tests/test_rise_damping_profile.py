import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from attitude import Fault
from self_righting_trial import rise_damping,SelfRightingController
from self_righting_lift_trial import LIFT_PLAN
from self_righting_rate_profile import RATE_PROFILE_PLAN,main
from air_trial import run
from test_attitude_air import CAL
from test_self_righting import TraceIMU
from test_wheel_check import Bus


class RiseDampingTests(unittest.TestCase):
    def test_default_does_not_open_hardware(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_profile_symmetric_continuous_and_preserves_other_limits(self):
        p=RATE_PROFILE_PLAN
        for sign in (-1,1):
            for angle,kd in ((0,.12),(20,.12),(35,.075),(50,.03),(90,.03)):
                self.assertAlmostEqual(rise_damping(sign*angle,p),kd)
        for edge in (20.,50.):
            self.assertLess(abs(rise_damping(edge-1e-5,p)-rise_damping(edge+1e-5,p)),1e-6)
        for key in ('predicted_net_torque_limit_nm','control_torque_limit_nm','rise_speed_target_rad_s',
                    'rise_wheel_speed_limit_rad_s','estimated_torque_limit_nm','temperature_limit_c',
                    'capture_pitch_deg','capture_rate_dps'):
            self.assertEqual(p[key],LIFT_PLAN[key])
        self.assertEqual(rise_damping(40,LIFT_PLAN),LIFT_PLAN['rise_kd_nm_per_rad_s'])

    def test_invalid_profile_fails_before_enable(self):
        for edit in ({'rise_near_kd_nm_per_rad_s':.21},{'rise_far_kd_nm_per_rad_s':0.},
                     {'rise_damping_near_pitch_deg':51.}):
            bus=Bus();report={}
            run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,stuck=True),CAL,report,False,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,
                plan=dict(RATE_PROFILE_PLAN,**edit),controller=SelfRightingController())
            self.assertEqual(bus.maximum_enabled,0)
            self.assertTrue(report['final_disabled_verified'])


if __name__=='__main__':unittest.main()
