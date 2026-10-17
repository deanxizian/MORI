"""Lateral acceleration rejection while retaining genuine roll rejection."""
import copy
import io
import math
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from attitude import PitchEstimator, Fault
from ground_ardupilot_balance import ArduPilotBalanceController
from test_attitude_air import CAL
from two_deck_balance import main as retired_main
from two_deck_fused_roll import PLAN, main


def sample(t, acceleration, gyro=(0.,0.,0.)):
    return dict(t_read_complete=t,accel_g=list(acceleration),gyro_dps=list(gyro))


class RollTests(unittest.TestCase):
    def test_acceleration_pulse_is_not_instantaneous_physical_roll(self):
        old=PitchEstimator(copy.deepcopy(CAL));fused=PitchEstimator(copy.deepcopy(CAL),fuse_roll=True)
        for e in (old,fused):e.update(sample(1.,(0.,0.,1.)))
        pulse=sample(1.005,(-.6473,-.2274,1.0889),(-.061,32.379,12.878))
        a=old.update(pulse);b=fused.update(pulse)
        self.assertGreater(abs(a['roll_deg']),8.)
        with self.assertRaisesRegex(Fault,'body_tilt_stop'):
            ArduPilotBalanceController()(a,{0:0.,1:0.},PLAN)
        self.assertLess(abs(b['roll_deg']),1.)
        ArduPilotBalanceController()(b,{0:0.,1:0.},PLAN)

    def test_real_roll_still_stops_before_motor_output(self):
        e=PitchEstimator(copy.deepcopy(CAL),fuse_roll=True)
        e.update(sample(1.,(0.,0.,1.)))
        for i in range(1,101):
            roll=math.radians(i*.1)
            a=e.update(sample(1.+i*.005,(0.,-math.sin(roll),math.cos(roll)),(-20.,0.,0.)))
        self.assertGreater(a['roll_deg'],8.)
        with self.assertRaisesRegex(Fault,'body_tilt_stop'):
            ArduPilotBalanceController()(a,{0:0.,1:0.},PLAN)

    def test_default_inert_and_faulted_baseline_held(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                retired_main(['--run-two-deck-balance','--operator-ready',
                              '--port','unused','--output','unused','--calibration','unused'])


if __name__ == '__main__':unittest.main()
