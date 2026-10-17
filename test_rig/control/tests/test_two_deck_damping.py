import io
import struct
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from air_trial import torque_packet
from ground_ardupilot_balance import ArduPilotBalanceController
from protocol import RATIO
from test_ardupilot_balance import pose
from two_deck_fused_roll import PLAN as OLD,main as retired_main
from two_deck_lower_damping import PLAN,main


def encoded_net(command,speed,plan):
    ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(0,command,plan),4)
    return ff/256000*RATIO-kd/128000000*RATIO**2*speed


class DampingTests(unittest.TestCase):
    def test_both_drive_directions_have_authority_without_raising_net_budget(self):
        for sign in (-1,1):
            speeds={0:sign*3.,1:sign*3.}
            old=ArduPilotBalanceController()(pose(.005,pitch=sign*5),speeds,OLD)
            new=ArduPilotBalanceController()(pose(.005,pitch=sign*5),speeds,PLAN)
            self.assertLess(abs(encoded_net(old[0],speeds[0],OLD)),.05)
            self.assertGreater(abs(encoded_net(new[0],speeds[0],PLAN)),.08)
            for v in (-3.99,0.,3.99):
                commands=ArduPilotBalanceController()(pose(.005,pitch=sign*5),{0:v,1:v},PLAN)
                for cmd in commands.values():
                    self.assertLessEqual(abs(cmd),.12)
                    self.assertLessEqual(abs(encoded_net(cmd,v,PLAN)),.12000000001)

    def test_single_parameter_comparison_and_inert_retired_entry(self):
        ignored={'name','motion_hold_reason'}
        self.assertEqual({k for k in OLD if k not in ignored and OLD[k]!=PLAN[k]},
                         {'native_wheel_damping_nm_per_rad_s'})
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                retired_main(['--run-two-deck-fused-roll','--operator-ready',
                              '--port','unused','--output','unused','--calibration','unused'])


if __name__=='__main__':unittest.main()
