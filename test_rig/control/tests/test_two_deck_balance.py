"""Upright-only workflow and actual encoded limits; no physical plant model."""
import copy
import io
import struct
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from air_trial import run, torque_packet
from attitude import Fault
from ground_ardupilot_balance import ArduPilotBalanceController
from ground_hold_trial import HoldTravel
from protocol import RATIO
from self_righting_governor_stronger import main as retired_main
from test_ardupilot_balance import pose
from test_attitude_air import CAL
from test_rate200 import RateIMU
from test_wheel_check import Bus
from two_deck_balance import PLAN, main


class TwoDeckTests(unittest.TestCase):
    def test_default_inert_and_unused_swingup_entry_retired_before_io(self):
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('file IO')), \
             patch('air_trial.run', side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 0)
            with self.assertRaises(SystemExit):
                retired_main(['--run-stronger-governor','--operator-ready',
                              '--ack-query-timeout','--port','unused',
                              '--calibration','unused','--output','unused'])

    def test_fallen_pose_cannot_produce_upright_torque(self):
        for pitch in (-90., -20.01, 20.01, 90., 180.):
            with self.assertRaisesRegex(Fault, 'body_tilt_stop'):
                ArduPilotBalanceController()(pose(.005,pitch=pitch),{0:0.,1:0.},PLAN)

    def test_both_direction_packets_keep_net_budget_with_native_damping(self):
        for sign in (-1,1):
            for speed in (-3.99,0.,3.99):
                speeds={0:speed,1:-speed}
                commands=ArduPilotBalanceController()(pose(.005,pitch=sign*2),speeds,PLAN)
                for mid,command in commands.items():
                    ff,omega,position,kp,kd=struct.unpack_from('<hhihh',torque_packet(mid,command,PLAN),4)
                    net=ff/256000*RATIO-kd/128000000*RATIO**2*speeds[mid]
                    self.assertLessEqual(abs(command),.12)
                    self.assertLessEqual(abs(net),.12000000001)
                    self.assertEqual((omega,position,kp),(0,0,0))

    def test_200hz_upright_run_has_no_rising_phase_and_always_stops(self):
        for fail in (False,True):
            bus=Bus(timeout=True,fail=(lambda m,p,phase: fail and m==1 and phase=='ground_two_deck_pid'))
            report={}
            run({m:bus.exchange(m) for m in (0,1)},RateIMU(bus,.005),copy.deepcopy(CAL),report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=ArduPilotBalanceController(),travel_factory=HoldTravel)
            self.assertEqual(report['status'],'FAIL' if fail else 'PASS')
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(report['balanced_operation'],'NOT_TESTED')
            self.assertEqual(report['requested_control_hz'],200)
            phases={phase for _,_,phase in bus.log}
            self.assertIn('ground_two_deck_pid',phases)
            self.assertFalse(any('rising' in phase.lower() or 'pre_roll' in phase.lower() for phase in phases))
            first=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[first:]))


if __name__ == '__main__':
    unittest.main()
