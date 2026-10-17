from contextlib import redirect_stdout,redirect_stderr
import io
import math
import struct
import unittest
from unittest.mock import patch

import wheel_rate_probe as probe
from attitude import Fault
from protocol import RATIO,crc32_words
from test_attitude_air import CAL


class RateBus:
    """Deterministic test fixture, not an identified physical motor model."""
    def __init__(self,fault=None,stall=False):
        self.t=0.;self.log=[];self.max_enabled=0;self.fault=fault;self.stall=stall
        self.states={m:dict(mode=0,v=0.,p=0.,last=0.) for m in (0,1)}
    def now(self):return self.t
    def sleep(self,dt):self.t+=dt
    def exchange(self,mid):
        def call(packet,phase):
            self.log.append((mid,packet,phase));s=self.states[mid]
            dt=self.t-s['last'];s['last']=self.t;s['p']+=s['v']*dt
            s['mode']=(packet[2]>>4)&7
            raw,speed,pos,kp,rawkd=struct.unpack_from('<hhihh',packet,4)
            assert (pos,kp)==(0,0)
            ff=raw*RATIO/256000.;kd=rawkd*RATIO**2/128000000.
            desired=speed*math.tau/(RATIO*2.56)
            if s['mode'] and not self.stall:
                s['v']+=dt*(ff+kd*(desired-s['v'])-.02*s['v'])/.008
            else:s['v']=0.
            self.max_enabled=max(self.max_enabled,sum(v['mode']==1 for v in self.states.values()))
            row=dict(id=mid,mode=s['mode'],speed_rad_s=s['v'],position_rad=s['p'],
                absolute_output_rad=s['p']%math.tau,torque_estimate_nm=ff+kd*(desired-s['v']),
                temperature_c=40,voltage_v=12.,errors_raw=0,warning_raw=0,
                timeout_active=False,feedback_received_monotonic=self.t)
            if self.fault and phase=='rate_probe' and mid==0:self.fault(row)
            return row
        return call


class WheelRateProbeTests(unittest.TestCase):
    def run_bus(self,bus):
        report={};probe.run({m:bus.exchange(m) for m in (0,1)},CAL,report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None)
        return report

    def assert_no_rearm_after_stop(self,bus):
        k=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
        self.assertTrue(all((p[2]&0x70)==0 for _,p,_ in bus.log[k:]))

    def test_default_no_io_and_unlock_required(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')), \
             patch('wheel_rate_probe.run',side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(probe.main([]),0)
            with self.assertRaises(SystemExit):probe.main(['--run-wheel-rate-probe','--operator-ready'])
        self.assertEqual(probe.PLAN['max_phase_s'],2.)
        self.assertEqual(probe.PLAN['max_temperature_c'],70)
        for t,target in ((0,0),(.2,.1),(.4,.2),(1.2,.2),(1.4,.1),(1.6,0),(2,0)):
            self.assertAlmostEqual(probe.desired_rate(t),target)

    def test_four_signed_phases_one_enabled_and_zero_mode_between(self):
        b=RateBus();r=self.run_bus(b)
        self.assertEqual(r['status'],'PASS',r.get('reason'))
        self.assertTrue(r['final_disabled_verified']);self.assertEqual(b.max_enabled,1)
        self.assertEqual([(p['id'],p['protocol_direction']) for p in r['phases']],
                         [(0,1),(0,-1),(1,-1),(1,1)])
        for p in r['phases']:
            self.assertTrue(2<=p['elapsed_s']<2.02)
            self.assertTrue(p['motion_seen'])
            self.assertTrue(all(abs(s['control']['command_ff_nm'])<=.08 for s in p['samples']))
            self.assertTrue(all(abs(s['control']['predicted_net_nm'])<=.08+1e-12 for s in p['samples']))
        self.assertEqual(r['balanced_operation'],'NOT_APPLICABLE')
        self.assertEqual(r['rate_tracking_qualified'],'NOT_TESTED')

    def test_faults_stop_and_cancel_remaining_phases(self):
        for field,value,reason in (('speed_rad_s',.61,'wheel_speed_stop'),
                ('temperature_c',70,'temperature_stop'),
                ('torque_estimate_nm',.121,'estimated_torque_stop'),
                ('feedback_received_monotonic',-1.,'wheel_rate_stale_feedback')):
            with self.subTest(field=field):
                b=RateBus(fault=lambda r:r.update({field:value}));r=self.run_bus(b)
                self.assertEqual(r['status'],'FAIL');self.assertEqual(r['reason'],reason)
                self.assertTrue(r['final_disabled_verified']);self.assertEqual(len(r['phases']),1)
                self.assert_no_rearm_after_stop(b)
        b=RateBus(stall=True);r=self.run_bus(b)
        self.assertEqual(r['reason'],'no_low_speed_response_within_fixed_window')
        self.assertTrue(r['final_disabled_verified']);self.assert_no_rearm_after_stop(b)

    def test_exact_packet_caps_integral_bounded_and_phase_state_is_fresh(self):
        c=probe.RateCommand()
        for i in range(500):
            allocation,info=c.update(.2,0.,.01)
            self.assertLessEqual(abs(info['command_ff_nm']),.08)
            self.assertLessEqual(abs(info['predicted_net_nm']),.08+1e-12)
            self.assertLessEqual(abs(info['pid']['i']),75.)
            p=probe.packet(0,allocation)
            self.assertEqual(struct.unpack_from('<hhihh',p,4),
                (allocation.feedforward_raw,0,0,0,allocation.native_kd_raw))
            self.assertEqual(struct.unpack_from('<I',p,16)[0],crc32_words(p[:16]))
        fresh=probe.RateCommand();a,d=fresh.update(0.,0.,.01)
        self.assertEqual(a.feedforward_raw,0);self.assertEqual(d['pid']['i'],0.)
        with self.assertRaisesRegex(Fault,'target_cap'):fresh.update(.201,0,.01)
        with self.assertRaisesRegex(Fault,'wheel_speed'):fresh.update(.2,.601,.01)

    def test_second_zero_arm_motion_cancels_rest_without_rearm(self):
        # Regression for trial35: a completed first phase is not permission
        # to ignore motion on the next arm. No second ramp or right-wheel
        # enable may follow the rejected zero-arm feedback.
        b=RateBus();left=b.exchange(0);arms=0;failure_index=None
        def exchange_left(packet,phase):
            nonlocal arms,failure_index
            row=left(packet,phase)
            if phase=='arm_zero_transition':arms+=1
            if arms==2 and phase=='arm_zero_settle':
                row['speed_rad_s']=-.21
                failure_index=len(b.log)-1
            return row
        r={}
        probe.run({0:exchange_left,1:b.exchange(1)},CAL,r,True,
                  now=b.now,sleep=b.sleep,display=lambda _:None)
        self.assertEqual(r['reason'],'unexpected_zero_arm_motion')
        self.assertEqual(len(r['phases']),1)
        self.assertEqual(r['phases'][0]['status'],'PASS')
        self.assertTrue(r['final_disabled_verified'])
        self.assertIsNotNone(failure_index)
        self.assertTrue(all((p[2]&0x70)==0 for _,p,_ in b.log[failure_index+1:]))
        self.assertFalse(any(mid==1 and p[2]&0x70 for mid,p,_ in b.log))

    def run_arm_fixture(self,modify):
        b=RateBus();left=b.exchange(0);arm_begin=None
        def exchange_left(packet,phase):
            nonlocal arm_begin
            row=left(packet,phase)
            if phase=='arm_zero_transition':arm_begin=b.now()
            if phase=='arm_zero_settle':modify(row,b.now()-arm_begin)
            return row
        r={};probe.run({0:exchange_left,1:b.exchange(1)},CAL,r,True,
            now=b.now,sleep=b.sleep,display=lambda _:None)
        return b,r

    def test_small_arm_transient_must_settle_before_first_ramp(self):
        # Synthetic readiness feedback, not a physical response model.
        b,r=self.run_arm_fixture(lambda row,t:row.update(speed_rad_s=-.06 if t<.3 else 0.))
        self.assertEqual(r['status'],'PASS',r.get('reason'))
        self.assertEqual(len(r['phases']),4)
        for arm in r['arming']:
            self.assertGreaterEqual(arm['quiet_dwell_s'],.2)
            if arm['id']==0:self.assertGreaterEqual(arm['elapsed_s'],.49)
            self.assertLessEqual(arm['elapsed_s'],.8)
        self.assertTrue(r['final_disabled_verified'])

    def test_persistent_small_arm_motion_times_out_without_ramp(self):
        b,r=self.run_arm_fixture(lambda row,t:row.update(speed_rad_s=.06))
        self.assertEqual(r['reason'],'zero_arm_settle_timeout')
        self.assertEqual(r['phases'],[])
        self.assertTrue(r['final_disabled_verified'])
        self.assert_no_rearm_after_stop(b)

    def test_arm_rotor_and_output_excursion_still_stop_without_ramp(self):
        for field,delta in [('position_rad',math.radians(1.01)),
                            ('absolute_output_rad',math.radians(3.01))]:
            with self.subTest(field=field):
                b,r=self.run_arm_fixture(lambda row,t:row.update({field:row[field]+delta}))
                self.assertEqual(r['reason'],'unexpected_zero_arm_displacement')
                self.assertEqual(r['phases'],[])
                self.assertTrue(r['final_disabled_verified'])
                self.assert_no_rearm_after_stop(b)

    def test_native_speed_wire_values_and_sampled_net_budget(self):
        c=probe.NativeVelocityCommand()
        for target in (-.2,-.119,0.,.119,.2):
            for speed in (-.6,-.2,0.,.2,.6):
                a,info=c.update(target,speed,.01)
                p=probe.packet(0,a)
                ff,raw_speed,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
                self.assertEqual((ff,pos,kp),(0,0,0))
                actual_target=raw_speed*math.tau/(RATIO*2.56)
                self.assertLessEqual(abs(actual_target),abs(target)+1e-12)
                actual_kd=kd*RATIO**2/128000000.
                self.assertLessEqual(actual_kd,1.2)
                self.assertAlmostEqual(actual_kd*(actual_target-speed),a.predicted_net_nm)
                self.assertLessEqual(abs(a.predicted_net_nm),.08+1e-12)
                self.assertFalse(info['host_integral_enabled'])
                self.assertEqual(struct.unpack_from('<I',p,16)[0],crc32_words(p[:16]))

    def test_native_controller_does_not_call_host_pi_or_accumulate_integral(self):
        with patch.object(probe.WheelRateStage,'update',side_effect=AssertionError('host PI called')):
            c=probe.NativeVelocityCommand()
            first=c.update(.2,0.,.01)
            for _ in range(50):self.assertEqual(c.update(.2,0.,.01),first)
            a,info=c.update(0.,0.,.01)
            self.assertEqual(a.velocity_raw,0)
            self.assertEqual(a.feedforward_raw,0)
            self.assertEqual(a.predicted_net_nm,0.)
            self.assertFalse(info['host_integral_enabled'])

    def test_native_ramp_gain_does_not_raise_zero_arm_damping(self):
        b=RateBus();r=self.run_bus(b)
        self.assertEqual(r['status'],'PASS',r.get('reason'))
        arms=[p for _,p,phase in b.log if phase in ('arm_zero_transition','arm_zero_settle') and p[2]&0x70]
        self.assertTrue(arms)
        for p in arms:
            ff,speed,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
            self.assertEqual((ff,speed,pos,kp),(0,0,0,0))
            actual_kd=kd*RATIO**2/128000000.
            self.assertLessEqual(actual_kd,.4)
            self.assertLessEqual(actual_kd*probe.PLAN['max_zero_settle_speed_rad_s'],.08)
        ramp_kd=[struct.unpack_from('<hhihh',p,4)[-1]*RATIO**2/128000000.
                 for _,p,phase in b.log if phase=='rate_probe' and p[2]&0x70]
        self.assertGreater(max(ramp_kd),.79)


if __name__=='__main__':unittest.main()
