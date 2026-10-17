"""Outer-loop signs, state bounds and real runner fault handling, no plant claim."""
from contextlib import redirect_stdout
import copy
import io
import math
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from ground_travel_window import TRAVEL_WINDOW_PLAN
from ground_velocity_hold import VELOCITY_HOLD_PLAN, VelocityHoldController, main
from test_attitude_air import CAL, IMU
from test_wheel_check import Bus


def pose(t,pitch=0.,rate=0.,roll=0.):
    return dict(t=t,dt=.01,pitch_deg=pitch,pitch_error_deg=pitch,
                pitch_rate_dps=rate,roll_deg=roll)


class VelocityHoldTests(unittest.TestCase):
    def run_case(self,changes=None,imu_delay=False):
        bus=Bus(timeout=True);report={};exchanges={m:bus.exchange(m) for m in (0,1)}
        if changes:
            mid,field,value=changes;original=exchanges[mid]
            def changed(packet,phase):
                row=original(packet,phase)
                return dict(row,**{field:value}) if phase=='ground_pd' else row
            exchanges[mid]=changed
        run(exchanges,IMU(bus,delay=imu_delay),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda s:None,
            plan=VELOCITY_HOLD_PLAN,controller=VelocityHoldController(),travel_factory=HoldTravel)
        return bus,report

    def assert_stopped(self,bus,report):
        self.assertTrue(report['final_disabled_verified'])
        first=next(i for i,(_,_,p) in enumerate(bus.log) if p=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[first:]))
        self.assertEqual({m for m,_,p in bus.log if p=='stop_confirm'},{0,1})

    def test_default_does_no_io_and_does_not_relax_any_stop(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertEqual({k for k in TRAVEL_WINDOW_PLAN if TRAVEL_WINDOW_PLAN[k]!=VELOCITY_HOLD_PLAN[k]},
                         {'name','active_message'})
        self.assertNotIn('speed_ki',VELOCITY_HOLD_PLAN)

    def test_forward_backward_speed_request_opposite_reference(self):
        for direction in (-1,1):
            c=VelocityHoldController()
            for i in range(1,151):
                a=pose(i*.01);commands=c(a,{0:direction,1:direction})
            h=a['velocity_hold']
            self.assertLess(h['pitch_reference_deg']*direction,0)
            self.assertAlmostEqual(h['pitch_reference_deg'],-direction*math.degrees(.25*.04),places=2)
            # To first lean backwards, the wheels briefly move under the body:
            # same torque sign as the velocity. Do not negate this as a brake.
            self.assertTrue(all(v*direction>0 for v in commands.values()))
        c=VelocityHoldController();a=pose(.01)
        c(a,{0:1,1:-1})
        self.assertEqual(a['velocity_hold']['pitch_reference_deg'],0)

    def test_reference_cap_slew_and_fresh_run_state(self):
        c=VelocityHoldController();previous=0.
        for i in range(1,401):
            direction=1 if i<200 else -1
            a=pose(i*.01);commands=c(a,{0:direction*2,1:direction*2})
            ref=a['velocity_hold']['pitch_reference_deg']
            self.assertLessEqual(abs(ref),1.)
            self.assertLessEqual(abs(ref-previous),.020000001)
            self.assertTrue(all(abs(v)<=.12 for v in commands.values()))
            previous=ref
        self.assertAlmostEqual(previous,1.,places=6)
        fresh=VelocityHoldController();a=pose(.01);self.assertEqual(fresh(a,{0:0,1:0}),{0:0,1:0})
        self.assertEqual(a['velocity_hold']['pitch_reference_deg'],0)

    def test_high_frequency_speed_is_filtered_and_zero_speed_has_no_windup(self):
        c=VelocityHoldController();filtered=[]
        for i in range(1,201):
            a=pose(i*.01);c(a,{0:1 if i%2 else -1,1:1 if i%2 else -1})
            filtered.append(a['velocity_hold']['filtered_velocity_proxy_m_s'])
        self.assertLess(max(map(abs,filtered[100:])),.002)
        for i in range(201,401):c(pose(i*.01),{0:1,1:1})
        for i in range(401,801):
            a=pose(i*.01);c(a,{0:0,1:0})
        self.assertLess(abs(a['velocity_hold']['pitch_reference_deg']),1e-7)

    def test_raw_attitude_speed_and_sample_guards_survive_reference_offset(self):
        cases=[(dict(pitch=12.1),{0:0,1:0},'body_tilt'),
               (dict(roll=8.1),{0:0,1:0},'body_tilt'),
               (dict(rate=101),{0:0,1:0},'body_rotation'),
               ({},{0:2.01,1:0},'wheel_speed'),
               ({},{0:float('nan'),1:0},'nonfinite')]
        for kwargs,speeds,reason in cases:
            with self.assertRaisesRegex(Fault,reason):VelocityHoldController()(pose(.01,**kwargs),speeds)
        c=VelocityHoldController();c(pose(.01),{0:0,1:0})
        with self.assertRaisesRegex(Fault,'sample_gap'):c(pose(.04),{0:0,1:0})

    def test_finite_runner_stops_without_claiming_balanced_operation(self):
        bus,report=self.run_case()
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(30<=report['elapsed_s']<30.02)
        self.assertEqual(report['run_neutral_pitch_deg'],0)
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')
        self.assertIn('velocity_hold',report['samples'][-1]['attitude'])
        self.assert_stopped(bus,report)

    def test_feedback_faults_stop_both_without_rearm(self):
        for mid in (0,1):
            for field,value,reason in [('temperature_c',70,'servo_temperature_stop'),
                                       ('torque_estimate_nm',.1306603652,'estimated_torque_stop'),
                                       ('speed_rad_s',2.01,'wheel_speed_stop')]:
                bus,report=self.run_case(changes=(mid,field,value))
                self.assertEqual(report['reason'],reason)
                self.assert_stopped(bus,report)

    def test_stale_imu_stops_both_with_stateful_outer_loop(self):
        bus,report=self.run_case(imu_delay=True)
        self.assertEqual(report['status'],'FAIL')
        self.assert_stopped(bus,report)


if __name__=='__main__':
    unittest.main()
