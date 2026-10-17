"""Regression for trial 20's measured inward recovery, without claiming a plant."""
from contextlib import redirect_stdout
import io
import struct
import unittest
from unittest.mock import patch

from air_trial import torque_packet
from attitude import Fault
from ground_ardupilot_balance import ArduPilotBalanceController
from ground_ardupilot_observe_long import LONG_PLAN
from ground_ardupilot_rate_window import RATE_PLAN,main
from protocol import RATIO
import test_ardupilot_balance as baseline


class RateWindowTests(unittest.TestCase):
    def test_only_rate_guard_changed_and_default_is_inert(self):
        self.assertEqual({k for k in LONG_PLAN if LONG_PLAN[k]!=RATE_PLAN[k]},
                         {'name','active_message','pitch_rate_limit_dps'})
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_recorded_inward_recovery_is_not_rejected_but_extremes_are(self):
        a=baseline.pose(.01,pitch=-5.350664737631856,rate=117.74591837660782,roll=-1.132885895163939)
        # Feedback immediately preceding the rejected IMU frame in trial 20.
        speeds={0:-2.0426,1:-1.4554}
        with self.assertRaisesRegex(Fault,'body_rotation_rate_stop'):
            ArduPilotBalanceController()(a.copy(),speeds,LONG_PLAN)
        commands=ArduPilotBalanceController()(a.copy(),speeds,RATE_PLAN)
        for mid,value in commands.items():
            ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(mid,value,RATE_PLAN),4)
            net=ff/256000*RATIO-kd/128000000*RATIO**2*speeds[mid]
            self.assertLessEqual(abs(value),.12)
            self.assertLessEqual(abs(net),.12000000001)
        for rate in (-200.1,200.1):
            with self.assertRaisesRegex(Fault,'body_rotation_rate_stop'):
                ArduPilotBalanceController()(baseline.pose(.01,rate=rate),{0:0.,1:0.},RATE_PLAN)
        for pitch in (-30.1,30.1):
            with self.assertRaisesRegex(Fault,'body_tilt_stop'):
                ArduPilotBalanceController()(baseline.pose(.01,pitch=pitch),{0:0.,1:0.},RATE_PLAN)


if __name__=='__main__':
    unittest.main()
