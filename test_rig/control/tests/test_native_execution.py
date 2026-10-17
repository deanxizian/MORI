import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import math
import struct
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from native_velocity_net_adapter import allocate_native_net
from protocol import RATIO,crc32_words
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_two_deck_heading import frame
from test_wheel_check import Bus
from two_deck_native_execution import PLAN,NativeExecutionController,main
from two_deck_velocity_diagnostics import PLAN as BEFORE,VelocityDiagnosticsController


class NativeExecutionTests(unittest.TestCase):
    def test_inert_default_unlock_and_original_ground_guards(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')), \
             patch('air_trial.run',side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):main(['--run-two-deck-native-execution','--operator-ready'])
        changed={'name','duration_s','control_phase','active_message'}
        self.assertEqual({k:v for k,v in BEFORE.items() if k not in changed},
                         {k:PLAN[k] for k in BEFORE if k not in changed})
        self.assertEqual(PLAN['duration_s'],10.)

    def test_allocator_exact_wire_oracle_across_polarity_and_budget_edges(self):
        for request in (-.4,-.12,-.1198,-.03,0.,.03,.1198,.12,.4):
            for speed in (-6.,-5.99,-2.,-.2,0.,.2,2.,5.99,6.):
                a=allocate_native_net(request,speed,native_kd=.4,velocity_limit_rad_s=6.,
                    feedforward_limit_nm=.12,net_budget_nm=.12,gear_ratio=RATIO)
                wire_ff=a.feedforward_raw*RATIO/256000.
                wire_speed=a.velocity_raw*math.tau/(RATIO*2.56)
                wire_kd=a.native_kd_raw*RATIO**2/128000000.
                decoded_net=wire_ff+wire_kd*(wire_speed-speed)
                self.assertLessEqual(abs(wire_ff),.12+1e-12)
                self.assertLessEqual(abs(wire_speed),6.)
                self.assertLessEqual(abs(decoded_net),.12+1e-12)
                self.assertAlmostEqual(decoded_net,a.predicted_net_nm)
                if not a.limited:
                    self.assertLessEqual(abs(decoded_net-request),a.torque_lsb_nm/2+1e-12)
                if abs(request)>.12:self.assertTrue(a.limited)
        edge=allocate_native_net(.12,6.,native_kd=.4,velocity_limit_rad_s=6.,
            feedforward_limit_nm=.12,net_budget_nm=.12,gear_ratio=RATIO)
        self.assertTrue(edge.limited);self.assertTrue(edge.velocity_reference_limited)
        self.assertTrue(.11<edge.predicted_net_nm<.12)
        for kwargs in ({'native_kd':0.},{'velocity_limit_rad_s':0.},
                       {'net_budget_nm':float('nan')},{'gear_ratio':-1.}):
            options=dict(native_kd=.4,velocity_limit_rad_s=6.,feedforward_limit_nm=.12,net_budget_nm=.12,gear_ratio=RATIO)
            options.update(kwargs)
            with self.assertRaises(ValueError):allocate_native_net(0.,0.,**options)

    def test_outer_pid_reference_and_differential_requests_are_retained(self):
        new=NativeExecutionController();old=VelocityDiagnosticsController()
        for i in range(1,201):
            t=i*.005;poses={0:.02*math.sin(t),1:.02*math.sin(t+.1)}
            a=frame(t,poses);a.update(pitch_deg=.2*math.sin(t*2),pitch_rate_dps=.4*math.cos(t*2))
            a['wheel_feedback_received_monotonic']={0:t-.003,1:t-.002}
            speeds={0:.1*math.sin(t),1:.1*math.sin(t+.1)};b=copy.deepcopy(a)
            commands=new(a,speeds,PLAN);old(b,speeds,BEFORE)
            self.assertEqual(a['velocity_hold'],b['velocity_hold'])
            self.assertEqual(a['wheel_sync'],b['wheel_sync'])
            self.assertEqual(a['ardupilot_balance']['requested_net_per_wheel_nm'],
                             b['ardupilot_balance']['requested_net_per_wheel_nm'])
            for mid,sign in ((0,1),(1,-1)):
                p=new.allocated_torque_packet(mid,sign,commands[mid],PLAN)
                ff,v,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
                self.assertEqual((pos,kp),(0,0))
                self.assertEqual(struct.unpack_from('<I',p,16)[0],crc32_words(p[:16]))
                net=sign*ff*RATIO/256000.+kd*RATIO**2/128000000.*(sign*v*math.tau/(RATIO*2.56)-speeds[mid])
                self.assertAlmostEqual(net,new.native_allocations[mid].predicted_net_nm)

    def test_zero_net_while_moving_and_between_sample_damping(self):
        a=allocate_native_net(0.,2.,native_kd=.4,velocity_limit_rad_s=6.,
            feedforward_limit_nm=.12,net_budget_nm=.12,gear_ratio=RATIO)
        self.assertGreater(a.velocity_raw,0)
        self.assertLessEqual(abs(a.predicted_net_nm),a.torque_lsb_nm/2+1e-12)
        kd=a.native_kd_raw*RATIO**2/128000000.
        torque_after_speed_increase=a.feedforward_nm+kd*(a.velocity_rad_s-2.01)
        self.assertAlmostEqual(torque_after_speed_increase-a.predicted_net_nm,-kd*.01)
        # This algebra is not an actuator/plant simulation or hardware clamp.

    def test_fault_or_reset_discards_all_previously_prepared_packets(self):
        c=NativeExecutionController();commands=c(frame(.005,{0:0.,1:0.}),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'command_changed'):
            c.allocated_torque_packet(0,1,commands[0]+.01,PLAN)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            c.allocated_torque_packet(0,1,commands[0],dict(PLAN,native_execution_kd=.8))
        with self.assertRaisesRegex(Fault,'sample_gap'):
            c(frame(.04,{0:0.,1:0.}),{0:0.,1:0.},PLAN)
        self.assertFalse(c.native_allocations)
        with self.assertRaisesRegex(Fault,'missing_or_invalid'):
            c.allocated_torque_packet(0,1,commands[0],PLAN)
        c.reset();self.assertIsNone(c.native_configuration)

    def test_runner_uses_native_packets_and_stops_without_fault_rearm(self):
        for fault_kind in ('none','link','cue'):
            b=Bus(timeout=True,fail=lambda m,p,phase:fault_kind=='link' and m==1 and phase==PLAN['control_phase'])
            report={};cue=Indicator(b,fault_kind=='cue')
            def tick():cue.check();cue.ticks+=1
            cue.tick=tick;c=NativeExecutionController()
            def exchange(mid):
                original=b.exchange(mid)
                def call(packet,phase):
                    row=original(packet,phase)
                    row['feedback_received_monotonic']=b.now()
                    return row
                return call
            with patch.object(c,'allocated_torque_packet',wraps=c.allocated_torque_packet) as hook:
                run({m:exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),report,True,
                    now=b.now,sleep=b.sleep,display=lambda _:None,
                    plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),controller=c,
                    travel_factory=HoldTravel,indicator=cue)
                self.assertGreater(hook.call_count,0)
            self.assertEqual(report['status'],'PASS' if fault_kind=='none' else 'FAIL',report.get('reason'))
            self.assertTrue(report['final_disabled_verified']);self.assertTrue(cue.off)
            stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
