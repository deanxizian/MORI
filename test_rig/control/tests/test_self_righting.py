"""Fault injection and prescribed traces only; no simulated robot proof."""
from contextlib import redirect_stdout
import io
import math
import struct
import unittest
from unittest.mock import patch

from air_trial import run,torque_packet
from attitude import Fault
from ground_hold_trial import HoldTravel
from protocol import RATIO
from self_righting_trial import SELF_RIGHT_PLAN,SelfRightingController,budget,main,rolling_speed
from test_attitude_air import CAL
from test_wheel_check import Bus


def pose(t,pitch=88.,rate=0.,positions=None):
    return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,roll_deg=0.,
                wheel_position_forward_rad=positions or {0:0.,1:0.})


def trace(t,sign=1.):
    if t<=.3:
        return 88.*sign,0.
    u=min(1.,(t-.3)/2.)
    return sign*44*(1+math.cos(math.pi*u)),(-sign*22*math.pi*math.sin(math.pi*u) if u<1 else 0.)


class TraceIMU:
    def __init__(self,bus,sign=1.,stuck=False,start_angle=88.):
        self.bus,self.sign,self.stuck,self.start_angle=bus,sign,stuck,start_angle
        self.active_t=None

    def sample(self):
        self.bus.sleep(.01)
        if self.active_t is None and any(phase=='self_righting' for _,_,phase in self.bus.log):
            self.active_t=self.bus.t
        pitch,rate=self.start_angle*self.sign,0.
        if self.active_t is not None and not self.stuck:
            pitch,rate=trace(self.bus.t-self.active_t,self.sign)
        return dict(t_read_complete=self.bus.t,
                    accel_g=[math.sin(math.radians(pitch)),0,math.cos(math.radians(pitch))],
                    gyro_dps=[0,-rate,0])


class SelfRightingTests(unittest.TestCase):
    def test_default_opens_no_hardware_and_profile_keeps_existing_output_caps(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertEqual(SELF_RIGHT_PLAN['feedforward_torque_limit_nm'],.12)
        self.assertEqual(SELF_RIGHT_PLAN['wheel_speed_limit_rad_s'],4.)
        self.assertEqual(SELF_RIGHT_PLAN['temperature_limit_c'],70)
        self.assertFalse(SELF_RIGHT_PLAN['capture_start_reference'])

    def test_encoder_body_correction_has_stationary_and_forward_cases(self):
        a=pose(.01,rate=90)
        self.assertAlmostEqual(rolling_speed(a,{0:-math.pi/2,1:-math.pi/2},SELF_RIGHT_PLAN),0.)
        self.assertAlmostEqual(rolling_speed(a,{0:0,1:0},SELF_RIGHT_PLAN),.04*math.pi/2)
        self.assertAlmostEqual(rolling_speed(pose(.01),{0:1,1:1},SELF_RIGHT_PLAN),.04)

    def test_arm_validation_never_starts_controller_and_rejects_upright(self):
        c=SelfRightingController()
        for t in (.01,.02,.03): c.validate_arm(pose(t),{0:0,1:0},SELF_RIGHT_PLAN)
        self.assertEqual(c.phase,'READY');self.assertIsNone(c.begin);self.assertIsNone(c.pid)
        for pitch in (0,74,-74,101,-101):
            with self.assertRaises(Fault): c.validate_arm(pose(.01,pitch),{0:0,1:0},SELF_RIGHT_PLAN)

    def test_both_directions_follow_synthetic_trace_and_require_stable_finish(self):
        for sign in (-1,1):
            c=SelfRightingController()
            for i in range(1000):
                t=i*.01;pitch,rate=trace(t,sign)
                a=pose(t+.01,pitch,rate)
                # World-stationary wheels: encoder rate cancels body rate.
                speeds={0:-math.radians(rate),1:-math.radians(rate)}
                command=c(a,speeds)
                self.assertTrue(all(abs(v)<=.12 for v in command.values()))
            c.finish()
            self.assertEqual([e['phase'] for e in c.events],['RISING','CAPTURE','BALANCE'])
            self.assertGreater(c.stable_s,2.)
            self.assertFalse(c.summary()['automatic_rearm'])

    def test_ramp_caps_before_scaling_even_when_large_error_saturates(self):
        c=SelfRightingController()
        first=c(pose(.01),{0:0,1:0})
        self.assertEqual(first,{0:0.,1:0.})
        for i in range(1,16):
            out=c(pose(.01+i*.01),{0:0,1:0})
            self.assertLessEqual(max(abs(v) for v in out.values()),.12*(i*.01)/.3+1e-10)

    def test_no_progress_fault_latches_until_new_explicit_controller_run(self):
        c=SelfRightingController()
        with self.assertRaisesRegex(Fault,'no_lift_progress'):
            for i in range(160): c(pose(i*.01),{0:0,1:0})
        with self.assertRaisesRegex(Fault,'fault_latched'):
            c(pose(1.61),{0:0,1:0})

    def test_wrong_way_fast_crossing_and_stale_data_reject(self):
        for initial,next_pose,reason in [
            (88.,pose(.02,94),'wrong_way'),
            (-88.,pose(.02,-94),'wrong_way'),
            (88.,pose(.02,-9,rate=-150),'uncaptured_overshoot'),
            (88.,pose(.04,87),'sample_gap'),
            (88.,pose(.02,88,rate=201),'body_rotation_rate_stop')]:
            c=SelfRightingController();c(pose(.01,initial),{0:0,1:0})
            with self.assertRaisesRegex(Fault,reason): c(next_pose,{0:0,1:0})
        c=SelfRightingController();c(pose(.01),{0:0,1:0})
        a=pose(.02,3,rate=-100);c(a,{0:0,1:0})
        self.assertEqual(c.phase,'RISING')

    def test_capture_lost_faults_instead_of_returning_to_rise(self):
        c=SelfRightingController();c(pose(.01),{0:0,1:0})
        c(pose(.02,7,rate=-10),{0:0,1:0})
        self.assertEqual(c.phase,'CAPTURE')
        with self.assertRaisesRegex(Fault,'capture_lost'): c(pose(.03,26),{0:0,1:0})
        self.assertEqual(c.phase,'FAULT')

    def test_forward_speed_requests_backward_pitch_and_reverse_is_symmetric(self):
        for direction in (-1,1):
            c=SelfRightingController();c(pose(.01),{0:0,1:0})
            for i in range(1,101):
                a=pose(.01+i*.01,0)
                c(a,{0:direction,1:direction})
            self.assertLess(c.pitch_target*direction,0)
            self.assertLessEqual(abs(c.pitch_target),2.5)

    def test_leading_wheel_receives_smaller_forward_request(self):
        c=SelfRightingController();c(pose(.01),{0:0,1:0})
        c(pose(.02,7),{0:0,1:0})
        for i in range(1,61):
            a=pose(.02+i*.01,0,positions={0:.1,1:0})
            out=c(a,{0:.1,1:0})
        self.assertLess(out[0],out[1])
        self.assertGreater(a['self_righting']['differential_correction_nm'],0)

    def test_actual_packet_quantization_retains_native_net_envelope(self):
        for speed0 in (-4,-1,0,1,4):
            for speed1 in (-4,0,4):
                speeds={0:speed0,1:speed1}
                for request in (-1,-.12,0,.12,1):
                    commands=budget({0:request-.025,1:request+.025},speeds,SELF_RIGHT_PLAN)
                    for mid in (0,1):
                        ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(mid,commands[mid],SELF_RIGHT_PLAN),4)
                        net=ff/256000*RATIO-kd/128000000*RATIO**2*speeds[mid]
                        self.assertLessEqual(abs(net),.12000000001)

    def run_trace(self,*,sign=1.,stuck=False,fail=False,temp=40,start_angle=88):
        bus=Bus(timeout=True,temp=temp,fail=(lambda mid,p,phase:mid==0 and phase=='self_righting') if fail else None)
        report={};c=SelfRightingController()
        run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,sign,stuck,start_angle),CAL,report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=SELF_RIGHT_PLAN,
            controller=c,travel_factory=HoldTravel)
        return bus,report

    def test_runner_full_trace_stops_without_claiming_physical_proof_from_a_test_trace(self):
        for sign in (-1,1):
            bus,report=self.run_trace(sign=sign)
            self.assertEqual(report['status'],'PASS',report.get('reason'))
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(report['balanced_operation'],'NOT_TESTED')
            self.assertEqual(report['controller_summary']['physical_self_righting'],'NOT_ASSESSED_BY_CONTROLLER')
            self.assertFalse(report['controller_summary']['operator_action_judgment_required'])
            countdown=[p for _,p,phase in bus.log if phase=='prearm_countdown_disabled']
            self.assertGreater(len(countdown),500)
            self.assertTrue(all(p[2]&0x70==0 for p in countdown))

    def test_runner_stall_or_bus_failure_stops_both_without_rearm(self):
        for kwargs in ({'stuck':True},{'fail':True}):
            bus,report=self.run_trace(**kwargs)
            self.assertEqual(report['status'],'FAIL')
            self.assertTrue(report['final_disabled_verified'])
            index=max(i for i,(_,_,phase) in enumerate(bus.log) if phase=='self_righting')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[index+1:]))

    def test_hot_or_upright_initial_pose_never_enables(self):
        for kwargs in ({'temp':70},{'start_angle':0}):
            bus,report=self.run_trace(**kwargs)
            self.assertEqual(report['status'],'FAIL')
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(bus.maximum_enabled,0)

    def test_rejected_acceleration_frame_is_saved_and_no_more_torque_is_sent(self):
        for magnitude in (.4,1.6):
            bus=Bus(timeout=True); report={}; source=TraceIMU(bus,stuck=True)
            original=source.sample; rejected={}
            def sample():
                raw=original()
                if any(phase=='self_righting' for _,_,phase in bus.log):
                    raw['accel_g']=[magnitude*v for v in raw['accel_g']]
                    rejected.update(raw=raw,index=len(bus.log))
                return raw
            source.sample=sample
            run({m:bus.exchange(m) for m in (0,1)},source,CAL,report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,
                plan=SELF_RIGHT_PLAN,controller=SelfRightingController(),travel_factory=HoldTravel)
            self.assertEqual(report['reason'],'acceleration_outside_test_window')
            self.assertEqual(report['rejected_imu_sample']['imu'],rejected['raw'])
            self.assertEqual(report['rejected_imu_sample']['phase'],'active_control')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[rejected['index']:]))
            self.assertTrue(report['final_disabled_verified'])

    def test_countdown_motion_is_saved_without_enabling_either_motor(self):
        bus=Bus(timeout=True); report={}; source=TraceIMU(bus,stuck=True)
        original=source.sample
        def sample():
            raw=original()
            if any(phase=='prearm_countdown_disabled' for _,_,phase in bus.log):
                raw['gyro_dps']=[0,-10,0]
            return raw
        source.sample=sample
        run({m:bus.exchange(m) for m in (0,1)},source,CAL,report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=SELF_RIGHT_PLAN,controller=SelfRightingController(),travel_factory=HoldTravel)
        self.assertEqual(report['reason'],'self_righting_start_not_still')
        self.assertEqual(report['rejected_arm_sample']['phase'],'prearm_countdown')
        self.assertEqual(report['rejected_arm_sample']['imu']['gyro_dps'],[0,-10,0])
        self.assertEqual(bus.maximum_enabled,0)
        self.assertTrue(report['final_disabled_verified'])


if __name__=='__main__':
    unittest.main()
