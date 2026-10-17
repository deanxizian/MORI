"""Recovery-window packet boundaries and finite/fault stops, no plant model."""
from contextlib import redirect_stdout
import io
import struct
import unittest
from unittest.mock import patch

from air_trial import torque_packet
from attitude import Fault
from ground_ardupilot_balance import ARDUPILOT_PLAN,ArduPilotBalanceController
from ground_ardupilot_recovery import RECOVERY_PLAN,main
from protocol import RATIO
import test_ardupilot_balance as baseline

pose=baseline.pose


class RecoveryWindowTests(unittest.TestCase):
    def test_default_is_inert_and_only_declared_parameters_change(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        changed={k for k in ARDUPILOT_PLAN if ARDUPILOT_PLAN[k]!=RECOVERY_PLAN[k]}
        self.assertEqual(changed,{'name','active_message','native_wheel_damping_nm_per_rad_s',
                                  'pitch_limit_deg','wheel_speed_limit_rad_s',
                                  'net_rolling_limit_m','rolling_path_limit_m'})
        self.assertEqual(RECOVERY_PLAN['arm_pitch_limit_deg'],8.)
        self.assertEqual(RECOVERY_PLAN['estimated_torque_limit_nm'],.12)
        self.assertEqual(RECOVERY_PLAN['temperature_limit_c'],70)

    def test_encoded_torque_bounds_at_all_window_edges_and_reversals(self):
        for pitch in (-29.9,-1.,0.,1.,29.9):
            for speed in (-3.99,-1.8,0.,1.8,3.99):
                commands=ArduPilotBalanceController()(pose(.01,pitch),{0:speed,1:-speed},RECOVERY_PLAN)
                for mid,cmd in commands.items():
                    ff,omega,position,kp,kd=struct.unpack_from('<hhihh',torque_packet(mid,cmd,RECOVERY_PLAN),4)
                    encoded_ff=ff/256000*RATIO
                    encoded_kd=kd/128000000*RATIO**2
                    predicted=encoded_ff-encoded_kd*(speed if mid==0 else -speed)
                    self.assertLessEqual(abs(cmd),.12)
                    self.assertLessEqual(abs(predicted),.12000000001)
                    self.assertTrue(0<encoded_kd<=.025)
                    self.assertEqual((omega,position,kp),(0,0,0))
        c=ArduPilotBalanceController()
        with self.assertRaisesRegex(Fault,'body_tilt_stop'):
            c(pose(.01,30.1),{0:0.,1:0.},RECOVERY_PLAN)
        with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
            c(pose(.01),{0:4.01,1:0.},RECOVERY_PLAN)

    def test_finite_runner_and_both_motor_fault_stops(self):
        harness=baseline.AdapterTests()
        result=harness.run_case(plan=RECOVERY_PLAN)
        self.assertEqual(result['status'],'PASS')
        self.assertTrue(15<=result['elapsed_s']<15.02)
        for mid in (0,1):
            for field,value,reason in [('temperature_c',70,'servo_temperature_stop'),
                                       ('torque_estimate_nm',.13,'estimated_torque_stop'),
                                       ('speed_rad_s',4.01,'wheel_speed_stop')]:
                result=harness.run_case((mid,field,value),plan=RECOVERY_PLAN)
                self.assertEqual(result['reason'],reason)
        self.assertEqual(harness.run_case(serial_fail=True,plan=RECOVERY_PLAN)['reason'],'injected_bus_failure')
        self.assertEqual(harness.run_case(imu_delay=True,plan=RECOVERY_PLAN)['status'],'FAIL')


if __name__=='__main__':
    unittest.main()
