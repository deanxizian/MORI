"""Protocol envelope and real runner faults; prescribed traces are not a plant."""
import io
import struct
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from air_trial import run, torque_packet
from ground_hold_trial import HoldTravel
from protocol import RATIO
from self_righting_trial import SelfRightingController, budget, govern_rise_speed
from attitude import Fault
from self_righting_lift_trial import LIFT_PLAN, main
from test_attitude_air import CAL
from test_self_righting import TraceIMU, pose
from test_wheel_check import Bus

PURE_RISE_PLAN=dict(LIFT_PLAN,pre_roll_duration_s=0.)
GOVERNED_PLAN=dict(PURE_RISE_PLAN,rise_speed_target_rad_s=8.,
                  rise_wheel_speed_limit_rad_s=12.,
                  rise_speed_gain_nm_per_rad_s=.1,rise_compensate_native_damping=True,
                  rise_native_wheel_damping_nm_per_rad_s=.01)


class LiftEnvelopeTests(unittest.TestCase):
    def test_position_rate_tightens_governor_before_filtered_feedback_catches_up(self):
        plan=dict(GOVERNED_PLAN,rise_speed_target_rad_s=11.,rise_speed_gain_nm_per_rad_s=.1)
        slow=govern_rise_speed({0:.35},{0:6.},plan,0.)[0]
        early=govern_rise_speed({0:.35},{0:6.},plan,0.,{0:9.})[0]
        self.assertAlmostEqual(slow,.35)
        self.assertAlmostEqual(early,.2)
        reverse=govern_rise_speed({0:-.35},{0:-6.},plan,0.,{0:-9.})[0]
        self.assertAlmostEqual(reverse,-early)
        self.assertEqual(govern_rise_speed({0:.35},{0:6.},plan,1.,{0:9.})[0],.35)
        with self.assertRaisesRegex(Fault,'inconsistent_velocity'):
            govern_rise_speed({0:.2},{0:-12.},plan,0.,{0:12.})

    def test_controller_records_position_rate_and_reduces_early_drive(self):
        plan=dict(PURE_RISE_PLAN,rise_speed_target_rad_s=11.,rise_speed_position_guard=True)
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},plan)
        for i in range(1,20):
            a=pose(.01+i*.01)
            a['wheel_position_forward_rad']={0:i*.09,1:i*.09}
            c(a,{0:6.,1:6.},plan)
        state=a['self_righting']
        self.assertAlmostEqual(state['position_derived_wheel_speed_rad_s'][0],9.)
        self.assertTrue(state['speed_governor_limited'])
        self.assertAlmostEqual(state['governed_net_request_nm'][0],.2)

    def test_governor_is_symmetric_brakes_overspeed_and_leaves_balance_unchanged(self):
        target=GOVERNED_PLAN['rise_speed_target_rad_s'];gain=GOVERNED_PLAN['rise_speed_gain_nm_per_rad_s']
        for speed in (0., 5., 7., 8., 9., 11.9):
            for request in (-.25, 0., .25):
                positive=govern_rise_speed({0:request},{0:speed},GOVERNED_PLAN,0.)[0]
                negative=govern_rise_speed({0:-request},{0:-speed},GOVERNED_PLAN,0.)[0]
                self.assertAlmostEqual(positive,-negative)
                self.assertLessEqual(positive,gain*(target-speed)+1e-12)
                self.assertGreaterEqual(positive,-gain*(target+speed)-1e-12)
                self.assertEqual(govern_rise_speed({0:request},{0:speed},GOVERNED_PLAN,1.)[0],request)
        self.assertEqual(govern_rise_speed({0:.25},{0:0.},GOVERNED_PLAN,0.)[0],.25)
        self.assertAlmostEqual(govern_rise_speed({0:.25},{0:target+1.},GOVERNED_PLAN,0.)[0],-gain)
        for target in (0.,12.,13.,float('nan')):
            with self.assertRaises(Fault):
                govern_rise_speed({0:.25},{0:0.},dict(GOVERNED_PLAN,rise_speed_target_rad_s=target),0.)

    def test_governor_reduces_actual_packet_net_torque_before_hard_stop(self):
        for sign in (-1.,1.):
            c=SelfRightingController();c(pose(.01,pitch=88.*sign),{0:0.,1:0.},GOVERNED_PLAN)
            drive=sign*GOVERNED_PLAN.get('rise_polarity',1)
            for i in range(1,21):
                a=pose(.01+i*.01,pitch=86.*sign)
                speeds={0:(GOVERNED_PLAN['rise_speed_target_rad_s']+1.)*drive,1:(GOVERNED_PLAN['rise_speed_target_rad_s']+1.)*drive}
                out=c(a,speeds,GOVERNED_PLAN)
            packet=torque_packet(0,out[0],c.motor_plan(GOVERNED_PLAN))
            ff,_,_,_,kd=struct.unpack_from('<hhihh',packet,4)
            net=ff/256000*RATIO-kd/128000000*RATIO**2*speeds[0]
            self.assertLess(net*drive,0.)
            self.assertAlmostEqual(net*drive,-.1,delta=RATIO/256000)
            self.assertTrue(a['self_righting']['speed_governor_limited'])
            self.assertTrue(a['self_righting']['output_limited'])
            with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
                c(pose(.22,pitch=86.*sign),{0:12.01*sign,1:9.*sign},GOVERNED_PLAN)

    def test_gentle_start_keeps_net_torque_growth_within_selected_ramp(self):
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},PURE_RISE_PLAN)
        for i in range(1,61):
            out=c(pose(.01+i*.01),{0:0.,1:0.},PURE_RISE_PLAN)
            allowed=LIFT_PLAN['control_torque_limit_nm']*min(1.,i*.01/LIFT_PLAN['rise_ramp_s'])
            self.assertTrue(all(abs(v)<=allowed+1e-12 for v in out.values()))

    def test_opposite_rising_polarity_does_not_invert_balance_controller(self):
        for sign in (-1.,1.):
            plan=dict(PURE_RISE_PLAN,rise_polarity=-1)
            c=SelfRightingController();c(pose(.01,pitch=88.*sign),{0:0.,1:0.},plan)
            for i in range(1,41):
                a=pose(.01+i*.01,pitch=88.*sign)
                out=c(a,{0:0.,1:0.},plan)
            self.assertTrue(all(v*sign<0. for v in out.values()))
            self.assertEqual(a['self_righting']['gyro_only_pitch_deg'],88.*sign)
        for polarity in (-1,1):
            c=SelfRightingController();plan=dict(PURE_RISE_PLAN,rise_polarity=polarity)
            c(pose(.01),{0:0.,1:0.},plan)
            for i in range(1,80):
                a=pose(.01+i*.01,pitch=2.)
                out=c(a,{0:0.,1:0.},plan)
            self.assertEqual(c.phase,'BALANCE')
            self.assertTrue(all(v>0. for v in out.values()))

    def test_default_is_no_io(self):
        with patch('builtins.open', side_effect=AssertionError('I/O')), redirect_stdout(io.StringIO()):
            self.assertEqual(main([]), 0)

    def test_packet_net_torque_both_directions_at_speed_extremes(self):
        for v0 in (-12., -8., -4., -1., 0., 1., 4., 8., 12.):
            for v1 in (-12., -8., -4., 0., 4., 8., 12.):
                speeds = {0: v0, 1: v1}
                for request in (-1., -.25, 0., .25, 1.):
                    for fraction in (0., .5, 1.):
                        out = budget({0: request-.025, 1: request+.025}, speeds, LIFT_PLAN, fraction)
                        for mid in (0, 1):
                            ff, _, _, _, kd = struct.unpack_from('<hhihh', torque_packet(mid, out[mid], LIFT_PLAN), 4)
                            actual_ff = ff/256000*RATIO
                            net = actual_ff-kd/128000000*RATIO**2*speeds[mid]
                            self.assertLessEqual(abs(actual_ff), LIFT_PLAN['feedforward_torque_limit_nm']+1e-11)
                            self.assertLessEqual(abs(net), LIFT_PLAN['predicted_net_torque_limit_nm']+1e-11)

    def test_net_request_compensates_quantized_damping_and_capture_removes_it(self):
        for speed in (-3., 3.):
            request=.15 if speed>0 else -.15
            out=budget({0:request,1:request},{0:speed,1:speed},LIFT_PLAN,1.)
            ff, _, _, _, kd=struct.unpack_from('<hhihh',torque_packet(0,out[0],LIFT_PLAN),4)
            net=ff/256000*RATIO-kd/128000000*RATIO**2*speed
            self.assertAlmostEqual(net,request,delta=RATIO/256000)
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},PURE_RISE_PLAN)
        c(pose(.02,7.),{0:0.,1:0.},PURE_RISE_PLAN)
        for i in range(1,70):
            a=pose(.02+i*.01,0.)
            c(a,{0:.1,1:.1},PURE_RISE_PLAN)
        self.assertEqual(c.phase,'BALANCE')
        self.assertEqual(a['self_righting']['native_damping_compensation_fraction'],0.)

    def test_fault_stops_both_no_retry(self):
        for stuck, hot, bus_fault in ((True, False, False), (False, True, False), (False, False, True)):
            bus = Bus(timeout=True, temp=70 if hot else 40,
                      fail=(lambda mid, p, phase: mid == 0 and phase == 'self_righting') if bus_fault else None)
            report = {}
            run({m: bus.exchange(m) for m in (0, 1)}, TraceIMU(bus, stuck=stuck), CAL, report, True,
                now=bus.now, sleep=bus.sleep, display=lambda _: None, plan=LIFT_PLAN,
                controller=SelfRightingController(), travel_factory=HoldTravel)
            self.assertEqual(report['status'], 'FAIL')
            self.assertTrue(report['final_disabled_verified'])
            if hot:
                self.assertEqual(bus.maximum_enabled, 0)
            else:
                last = max(i for i, (_, _, phase) in enumerate(bus.log) if phase == 'self_righting')
                self.assertTrue(all(p[2]&0x70 == 0 for _, p, _ in bus.log[last+1:]))

    def test_runner_packets_use_same_scheduled_damping_as_control_budget(self):
        bus=Bus(timeout=True); report={}
        run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus),CAL,report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=LIFT_PLAN,
            controller=SelfRightingController(),travel_factory=HoldTravel)
        self.assertEqual(report['status'],'PASS',report.get('reason'))
        for mid in (0,1):
            packets=[p for m,p,phase in bus.log if m==mid and phase=='self_righting']
            self.assertEqual(len(packets),len(report['samples']))
            for p,sample in zip(packets,report['samples']):
                a=sample['attitude']['self_righting'];kd=struct.unpack_from('<hhihh',p,4)[-1]
                requested=a['native_wheel_damping_nm_per_rad_s']
                self.assertAlmostEqual(kd/128000000*RATIO**2,requested,delta=RATIO**2/128000000)
                if a['phase']=='RISING':self.assertAlmostEqual(requested,LIFT_PLAN['rise_native_wheel_damping_nm_per_rad_s'])
                if a['phase']=='BALANCE':self.assertAlmostEqual(requested,.025)
        self.assertTrue(report['final_disabled_verified'])


if __name__ == '__main__':
    unittest.main()
