import io
import math
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_governor_stronger import PLAN,main
from self_righting_rate200 import PLAN as OLD,main as used_main
from self_righting_trial import govern_rise_speed,budget
from protocol import RATIO


class StrongerGovernorTests(unittest.TestCase):
    def test_only_gain_changes_with_speed_and_net_budget_retained(self):
        keys={'name','active_message','motion_hold_reason','rise_speed_gain_nm_per_rad_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in OLD.items() if k not in keys})
        self.assertEqual(PLAN['rise_speed_gain_nm_per_rad_s'],.35)
        self.assertEqual(PLAN['imu_odr_hz'],200)
        self.assertEqual(PLAN['wheel_speed_limit_rad_s'],16.5)
        self.assertEqual(PLAN['predicted_net_torque_limit_nm'],.35)

    def test_both_directions_intersect_worst_speed_and_downstream_budget(self):
        for sign in (-1,1):
            v={0:sign*14.5,1:sign*14.5};request={0:sign*.8,1:sign*.8}
            out=govern_rise_speed(request,v,PLAN,0.,v)
            self.assertAlmostEqual(out[0],sign*.35)
            brake=govern_rise_speed(request,v,PLAN,0.,{0:sign*16.,1:sign*16.})
            self.assertTrue(all(abs(x+sign*.175)<1e-10 for x in brake.values()))
            p=dict(PLAN,native_wheel_damping_nm_per_rad_s=.001,feedforward_torque_limit_nm=.6)
            ff=budget(out,v,p,compensation=1.)
            step=RATIO**2/128000000;kd=math.floor(.001/step)*step
            self.assertTrue(all(abs(ff[m]-kd*v[m])<=.350000001 for m in (0,1)))

    def test_default_inert_and_used_entry_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-rate200','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
