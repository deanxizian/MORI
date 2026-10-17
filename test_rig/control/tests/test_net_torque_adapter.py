import copy
import io
import math
import struct
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from net_torque_adapter import NetTorquePitchController
from protocol import RATIO,crc32_words
from test_ardupilot_balance import pose
from test_attitude_air import CAL
from test_rate200 import RateIMU
from test_wheel_check import Bus
from two_deck_net_torque import PLAN,main


class NetAdapterTests(unittest.TestCase):
    def test_default_does_no_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_exact_raw_commands_signs_and_net_budget(self):
        for pitch in (-19.,-1.,0.,1.,19.):
            for speed in (-3.99,-1.,0.,1.,3.99):
                c=NetTorquePitchController();a=pose(.005,pitch=pitch)
                speeds={0:speed,1:-speed};commands=c(a,speeds,PLAN)
                requested=a['ardupilot_balance']['requested_net_nm']
                for mid,cmd in commands.items():
                    sign=1 if mid==0 else -1
                    packet=c.allocated_torque_packet(mid,sign,cmd,PLAN)
                    ff,omega,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
                    allocation=c.allocations[mid]
                    self.assertEqual(ff,sign*allocation.feedforward_raw)
                    self.assertEqual((omega,pos,kp),(0,0,0))
                    self.assertEqual(kd,allocation.native_kd_raw)
                    self.assertEqual(struct.unpack_from('<I',packet,16)[0],crc32_words(packet[:16]))
                    net=sign*ff*RATIO/256000-kd*RATIO**2/128000000*speeds[mid]
                    self.assertLessEqual(abs(net),.12000000001)
                    self.assertLessEqual(abs(ff*RATIO/256000),.12)
                    if not allocation.limited:
                        self.assertLessEqual(abs(net-requested),allocation.torque_lsb_nm*.500001)

    def test_zero_net_at_nonzero_speed_is_compensated_and_reset_forgets_packets(self):
        c=NetTorquePitchController();commands=c(pose(.005),{0:2.,1:-2.},PLAN)
        self.assertGreater(commands[0],0.);self.assertLess(commands[1],0.)
        for a in c.allocations.values():
            self.assertLessEqual(abs(a.predicted_net_nm),a.torque_lsb_nm*.5)
        c.reset()
        with self.assertRaisesRegex(Fault,'missing_or_invalid'):
            c.allocated_torque_packet(0,1,commands[0],PLAN)

    def test_saturation_feedback_freezes_and_can_unwind_integral(self):
        c=NetTorquePitchController()
        for i in range(1,60): c(pose(i*.005,pitch=10.),{0:3.9,1:3.9},PLAN)
        self.assertTrue(c.previous_limited)
        previous=c.pid.integrator
        c(pose(.3,pitch=10.),{0:3.9,1:3.9},PLAN)
        self.assertEqual(c.pid.integrator,previous)
        c(pose(.305,pitch=-.2),{0:3.9,1:3.9},PLAN)
        self.assertLess(c.pid.integrator,previous)

    def test_mutations_and_stale_data_reject_before_packets(self):
        c=NetTorquePitchController();commands=c(pose(.005),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'command_changed'):
            c.allocated_torque_packet(0,1,commands[0]+.01,PLAN)
        with self.assertRaisesRegex(Fault,'budget_changed'):
            c.allocated_torque_packet(0,1,commands[0],dict(PLAN,native_wheel_damping_nm_per_rad_s=.02))
        with self.assertRaisesRegex(Fault,'sample_gap'):
            c(pose(.04),{0:0.,1:0.},PLAN)
        self.assertFalse(c.allocations)

    def test_runner_packet_hook_final_stop_and_feedback_fault(self):
        for fail in (False,True):
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase=='two_deck_net_torque_pid')
            report={};c=NetTorquePitchController()
            with patch.object(c,'allocated_torque_packet',wraps=c.allocated_torque_packet) as hook:
                run({m:bus.exchange(m) for m in (0,1)},RateIMU(bus,.005),copy.deepcopy(CAL),report,True,
                    now=bus.now,sleep=bus.sleep,display=lambda _:None,
                    plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),controller=c,travel_factory=HoldTravel)
                self.assertGreater(hook.call_count,0)
            self.assertEqual(report['status'],'FAIL' if fail else 'PASS')
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(report['balanced_operation'],'NOT_TESTED')
            stop=next(i for i,(_,_,p) in enumerate(bus.log) if p=='stop_transition')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[stop:]))


if __name__=='__main__':unittest.main()
