import copy
import io
import struct
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

from air_trial import run, torque_packet
from attitude import Fault
from ground_hold_trial import HoldTravel
from protocol import RATIO
from test_ardupilot_balance import pose
from test_attitude_air import CAL
from test_rate200 import RateIMU
from test_wheel_check import Bus
from two_deck_response_probe import PLAN, ResponseProbe, main
from two_deck_lower_damping import main as retired_main


class ResponseTests(unittest.TestCase):
    def test_default_inert_and_oscillating_version_retired(self):
        with patch('pathlib.Path.read_bytes', side_effect=AssertionError('IO')), \
             patch('air_trial.run', side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main([]), 0)
            with self.assertRaises(SystemExit):
                retired_main(['--run-two-deck-lower-damping', '--operator-ready'])

    def test_encoded_both_directions_and_damping_budget(self):
        for speed in (-3.99, 0., 3.99):
            c = ResponseProbe(); peak_pos = peak_neg = 0.
            for i in range(801):
                a = pose(1+i*.005); a['dt'] = .005
                speeds = {0:speed, 1:-speed}
                commands = c(a, speeds, PLAN)
                requested = a['response_probe']['requested_forward_ff_nm']
                peak_pos, peak_neg = max(peak_pos, requested), min(peak_neg, requested)
                for mid, command in commands.items():
                    sign = 1 if mid == 0 else -1
                    raw, omega, position, kp, kd = struct.unpack_from(
                        '<hhihh', torque_packet(mid, sign*command, PLAN), 4)
                    ff_forward = sign*raw/256000*RATIO
                    net = ff_forward-kd/128000000*RATIO**2*speeds[mid]
                    self.assertLessEqual(abs(ff_forward), .09)
                    self.assertLessEqual(abs(net), .12)
                    self.assertEqual((omega, position, kp), (0, 0, 0))
            self.assertEqual((peak_pos, peak_neg), (.09, -.09))

    def test_guarding_does_not_start_clock_and_invalid_data_faults(self):
        c = ResponseProbe()
        for i in range(100): c.validate_arm(pose(i*.005), {0:0., 1:0.}, PLAN)
        a = pose(5.); self.assertEqual(c(a,{0:0.,1:0.}),{0:0.,1:0.})
        self.assertEqual(a['response_probe']['elapsed_s'], 0.)
        with self.assertRaisesRegex(Fault, 'sample_gap'):
            c(pose(5.1),{0:0.,1:0.})
        for p, speeds, reason in [(21.,{0:0.,1:0.},'body_tilt'),
                                  (0.,{0:4.01,1:0.},'wheel_speed'),
                                  (0.,{0:0.},'requires_both')]:
            with self.assertRaisesRegex(Fault, reason):
                ResponseProbe()(pose(.005,pitch=p),speeds)

    def test_profile_mutation_is_rejected(self):
        c=ResponseProbe();c(pose(.005),{0:0.,1:0.})
        with self.assertRaisesRegex(Fault,'parameters_changed'):
            c(pose(.010),{0:0.,1:0.},dict(PLAN,probe_peak_ff_nm=.08))

    def test_finite_runner_and_fault_stop_both_without_rearm(self):
        for fail in (False, True):
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase=='two_deck_response_probe')
            report={}
            run({m:bus.exchange(m) for m in (0,1)},RateIMU(bus,.005),copy.deepcopy(CAL),report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,
                plan=dict(PLAN,post_stop_observation_s=0.),
                controller=ResponseProbe(),travel_factory=HoldTravel)
            self.assertEqual(report['status'],'FAIL' if fail else 'PASS')
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(report['balanced_operation'],'NOT_TESTED')
            if not fail:self.assertTrue(4. <= report['elapsed_s'] < 4.02)
            stop=next(i for i,(_,_,p) in enumerate(bus.log) if p=='stop_transition')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[stop:]))


if __name__ == '__main__': unittest.main()
