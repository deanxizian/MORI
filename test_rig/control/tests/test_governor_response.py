import io
import math
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_governor_response import PLAN,main
from self_righting_medium_transfer import PLAN as REFERENCE,main as used_main
from self_righting_trial import govern_rise_speed,budget
from protocol import RATIO


class GovernorResponseTests(unittest.TestCase):
    def test_only_gain_changes(self):
        keys={'name','active_message','motion_hold_reason','rise_speed_gain_nm_per_rad_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in REFERENCE.items() if k not in keys})
        self.assertEqual(PLAN['rise_speed_gain_nm_per_rad_s'],.25)
        self.assertEqual(PLAN['rise_speed_target_rad_s'],15.5)
        self.assertEqual(PLAN['wheel_speed_limit_rad_s'],16.5)

    def test_below_target_drive_and_worst_estimate_braking(self):
        v={0:14.5,1:14.5};requests={0:.35,1:.35}
        a=govern_rise_speed(requests,v,PLAN,0.,v)
        b=govern_rise_speed(requests,v,REFERENCE,0.,v)
        self.assertAlmostEqual(a[0],.25);self.assertAlmostEqual(b[0],.15)
        c=govern_rise_speed(requests,v,PLAN,0.,{0:16.,1:16.})
        self.assertTrue(all(abs(x+.125)<1e-10 for x in c.values()))

    def test_downstream_budget_still_caps_predicted_net(self):
        v={0:13.,1:13.}
        governed=govern_rise_speed({0:.8,1:.8},v,PLAN,0.,v)
        p=dict(PLAN,native_wheel_damping_nm_per_rad_s=.001,feedforward_torque_limit_nm=.6)
        ff=budget(governed,v,p,compensation=1.)
        step=RATIO**2/128000000;kd=math.floor(.001/step)*step
        self.assertTrue(all(abs(ff[m]-kd*v[m])<=.350000001 for m in (0,1)))

    def test_default_inert_and_used_entry_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-medium-transfer','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
