"""Upstream numeric fidelity plus actuator-boundary/fault checks; no plant claim."""
import copy
from contextlib import redirect_stdout
import io
import math
import random
import tempfile
import unittest
from unittest.mock import patch

from air_trial import run,torque_packet
from ardupilot_balance_core import BalancePitchPID
from attitude import Fault
from ground_ardupilot_balance import ARDUPILOT_PLAN,ArduPilotBalanceController,main
from ground_hold_trial import HoldTravel
from ground_travel_window import TRAVEL_WINDOW_PLAN
from protocol import RATIO
from test_attitude_air import CAL,IMU
from test_wheel_check import Bus
from ardupilot_oracle import build,calculate
import struct


def pose(t,pitch=0.,rate=0.,roll=0.):
    return dict(t=t,dt=.01,pitch_deg=pitch,pitch_error_deg=pitch,
                pitch_rate_dps=rate,roll_deg=roll)


class UpstreamParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory()
        cls.binary=build(cls.directory.name)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_port_matches_actual_upstream_cpp_functions(self):
        rng=random.Random(472)
        for filters in ((0.,0.,10.),(5.,10.,0.),(8.,6.,15.)):
            config=dict(kp=25.,ki=5.,kd=.05/.12,imax=.02/.12,
                        fltt=filters[0],flte=filters[1],fltd=filters[2],
                        ff=.2,dff=.03,pitch_ff=.4,pitch_max=math.radians(5),
                        limit_tc=.5,limit_threshold=.6)
            rows=[]
            for i in range(600):
                rows.append((.15*math.sin(i*.017),.12*math.sin(i*.033)+rng.uniform(-.003,.003),
                             rng.uniform(.008,.012),i%31<9,i==0 or i==350))
            reference=calculate(self.binary,config,rows)
            self.assertEqual(len(reference),len(rows))
            port=BalancePitchPID(**config)
            for row,wanted in zip(rows,reference):
                target,measurement,dt,limit,reset=row
                if reset:port.reset()
                output=port.update(target,measurement,dt,limit)
                info=port.info
                actual=[output,info['p'],info['i'],info['d'],info['ff'],
                        info['error_rad'],info['target_rad'],info['pitch_low_rad'],info['pitch_high_rad']]
                for got,expected in zip(actual,wanted):
                    self.assertAlmostEqual(got,expected,delta=2e-5)


class AdapterTests(unittest.TestCase):
    def test_default_no_devices_and_stop_boundaries_unchanged(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        changed={k for k in TRAVEL_WINDOW_PLAN if TRAVEL_WINDOW_PLAN[k]!=ARDUPILOT_PLAN[k]}
        self.assertEqual(changed,{'name','duration_s','control_phase','active_message'})
        self.assertEqual(ARDUPILOT_PLAN['ap_pitch_ff'],0.)

    def test_forward_and_backward_signs_and_first_derivative_reset(self):
        for direction in (-1,1):
            a=pose(.01,direction)
            cmd=ArduPilotBalanceController()(a,{0:0.,1:0.})
            self.assertTrue(all(v*direction>0 for v in cmd.values()))
            self.assertEqual(a['ardupilot_balance']['d_nm'],0.)
            self.assertAlmostEqual(a['ardupilot_balance']['p_nm'],3*math.radians(direction))

    def test_integral_is_bounded_freezes_on_limit_and_can_unwind(self):
        c=ArduPilotBalanceController()
        for i in range(1,301):
            a=pose(i*.01,.5);c(a,{0:0.,1:0.})
        self.assertGreater(a['ardupilot_balance']['i_nm'],.01)
        self.assertLessEqual(a['ardupilot_balance']['i_nm'],.02000000001)
        for i in range(301,340):
            a=pose(i*.01,10);c(a,{0:0.,1:0.})
        value=c.pid.integrator
        self.assertTrue(c.previous_limited)
        for i in range(340,380):c(pose(i*.01,10),{0:0.,1:0.})
        self.assertEqual(c.pid.integrator,value)
        c(pose(3.8,-1),{0:0.,1:0.})
        self.assertLess(c.pid.integrator,value)
        c.reset();a=pose(3.81);self.assertEqual(c(a,{0:0.,1:0.}),{0:0.,1:0.})

    def test_encoded_commands_remain_in_net_torque_envelope(self):
        for pitch in (-11.,11.):
            for speed in (-1.99,0.,1.99):
                a=pose(.01,pitch)
                commands=ArduPilotBalanceController()(a,{0:speed,1:-speed})
                for mid,cmd in commands.items():
                    packet=torque_packet(mid,cmd,ARDUPILOT_PLAN)
                    ff,omega,position,kp,kd=struct.unpack_from('<hhihh',packet,4)
                    predicted=ff/256000*RATIO-kd/128000000*RATIO**2*(speed if mid==0 else -speed)
                    self.assertLessEqual(abs(cmd),.12)
                    self.assertLessEqual(abs(predicted),.12000000001)
                    self.assertEqual((omega,position,kp),(0,0,0))

    def test_invalid_measurements_and_time_fault_before_output(self):
        cases=[(dict(pitch=12.1),{0:0.,1:0.},'body_tilt'),
               (dict(roll=8.1),{0:0.,1:0.},'body_tilt'),
               (dict(rate=101),{0:0.,1:0.},'body_rotation'),
               ({},{0:2.01,1:0.},'wheel_speed'),
               ({},{0:float('nan'),1:0.},'nonfinite'),
               ({},{0:0.},'requires_both')]
        for kwargs,speeds,reason in cases:
            with self.assertRaisesRegex(Fault,reason):ArduPilotBalanceController()(pose(.01,**kwargs),speeds)
        c=ArduPilotBalanceController();c(pose(.01),{0:0.,1:0.})
        with self.assertRaisesRegex(Fault,'sample_gap'):c(pose(.04),{0:0.,1:0.})

    def test_parameter_mutation_rejected_during_active_run(self):
        c=ArduPilotBalanceController();c(pose(.01),{0:0.,1:0.})
        with self.assertRaisesRegex(Fault,'parameters_changed'):
            c(pose(.02),{0:0.,1:0.},dict(ARDUPILOT_PLAN,ap_ki=4.))
        for changes in (dict(ap_imax=1.),dict(output_scale_nm=.2),dict(pitch_trim_forward_deg=2.)):
            with self.assertRaises(Fault):ArduPilotBalanceController()(pose(.01),{0:0.,1:0.},dict(ARDUPILOT_PLAN,**changes))

    def run_case(self,changes=None,imu_delay=False,serial_fail=False,plan=ARDUPILOT_PLAN):
        bus=Bus(timeout=True,fail=(lambda m,p,phase:m==1 and phase=='ground_ardupilot_pid') if serial_fail else None)
        report={};exchanges={m:bus.exchange(m) for m in (0,1)}
        if changes:
            mid,field,value=changes;original=exchanges[mid]
            def changed(packet,phase):
                row=original(packet,phase)
                return dict(row,**{field:value}) if phase=='ground_ardupilot_pid' else row
            exchanges[mid]=changed
        run(exchanges,IMU(bus,delay=imu_delay),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda s:None,
            plan=plan,controller=ArduPilotBalanceController(),travel_factory=HoldTravel)
        self.assertTrue(report['final_disabled_verified'])
        first=next(i for i,(_,_,p) in enumerate(bus.log) if p=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[first:]))
        self.assertEqual({m for m,_,p in bus.log if p=='stop_confirm'},{0,1})
        return report

    def test_runner_resets_unapplied_prearm_integral_and_stops_at_timeout(self):
        report=self.run_case()
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(15<=report['elapsed_s']<15.02)
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')
        self.assertTrue(report['controller_reset_before_active'])
        a=report['samples'][0]['attitude'];h=a['ardupilot_balance']
        self.assertTrue(h['filter_reset'])
        self.assertAlmostEqual(h['i_nm'],math.radians(a['pitch_deg'])*.6*a['dt'])

    def test_feedback_and_serial_fault_stop_both(self):
        for mid in (0,1):
            for field,value,reason in [('temperature_c',70,'servo_temperature_stop'),
                                       ('torque_estimate_nm',.13,'estimated_torque_stop'),
                                       ('speed_rad_s',2.01,'wheel_speed_stop')]:
                self.assertEqual(self.run_case((mid,field,value))['reason'],reason)
        self.assertEqual(self.run_case(serial_fail=True)['reason'],'injected_bus_failure')

    def test_stale_imu_stops_both_without_rearm(self):
        self.assertEqual(self.run_case(imu_delay=True)['status'],'FAIL')


if __name__=='__main__':
    unittest.main()
