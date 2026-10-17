import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch
from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains,with_gains
from output_encoder_velocity import OutputEncoderRates,OutputVelocityReference,OutputVelocityLiveController
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_tuning_temp80 import PLAN as OLD
from two_deck_live_output_velocity import PLAN,main


def feedback(t,angle0=0.,angle1=0.,rotor0=0.,rotor1=0.):
    return {m:dict(absolute_output_rad=angle,position_rad=rotor,feedback_received_monotonic=t)
            for m,angle,rotor in [(0,angle0,rotor0),(1,angle1,rotor1)]}


class OutputEncoderTests(unittest.TestCase):
    def test_unwrap_signs_standstill_and_feedback_freshness(self):
        t=OutputEncoderRates()
        t.observe(feedback(1.,math.tau-.001,.001),{0:1,1:-1})
        self.assertIsNone(t.velocity(1.001,.04))
        t.observe(feedback(1.005,.001,math.tau-.001,.002,-.002),{0:1,1:-1})
        for m in (0,1):self.assertAlmostEqual(t.position[m],.002);self.assertAlmostEqual(t.rates[m],.4)
        self.assertAlmostEqual(t.velocity(1.006,.04),.016)
        for stamp in (1.004,1.021):
            with self.assertRaisesRegex(Fault,'stale_or_future'):t.velocity(stamp,.04)
        t.observe(feedback(1.010,.001,math.tau-.001,.004,-.004),{0:1,1:-1})
        self.assertEqual(t.rates,{0:0.,1:-0.})

    def test_invalid_measurements_never_silently_fall_back(self):
        for f in [feedback(1.,math.tau,0.),feedback(1.,float('nan'),0.)]:
            with self.assertRaises(Fault):OutputEncoderRates().observe(f,{0:1,1:-1})
        for f in [feedback(1.005,1.,0.),feedback(1.),feedback(1.026)]:
            t=OutputEncoderRates();t.observe(feedback(1.),{0:1,1:-1})
            with self.assertRaises(Fault):t.observe(f,{0:1,1:-1})
        with self.assertRaises(Fault):OutputEncoderRates().observe({0:feedback(1.)[0]},{0:1,1:-1})

    def test_output_motion_owns_only_velocity_reference_not_raw_guard_or_allocator(self):
        t=OutputEncoderRates();v=OutputVelocityReference(t)
        t.observe(feedback(1.),{0:1,1:-1})
        t.observe(feedback(1.005,0.,0.,.005,-.005),{0:1,1:-1})
        a=sample(1.006)
        v(a,{0:1.,1:1.},PLAN)
        self.assertEqual(a['velocity_hold']['encoder_velocity_proxy_m_s'],.04)
        self.assertEqual(a['velocity_hold']['control_velocity_proxy_m_s'],0.)
        with self.assertRaisesRegex(Fault,'wheel_speed'):
            v(sample(1.012),{0:7.,1:0.},PLAN)
        c=OutputVelocityLiveController(TuningChannel(gains(PLAN)))
        out=c(sample(.005),{0:1.,1:1.},PLAN)
        for m,sign in [(0,1),(1,-1)]:
            self.assertLessEqual(abs(c.allocations[m].feedforward_nm),.12)
            self.assertLessEqual(abs(c.allocations[m].predicted_net_nm),.12)
            self.assertEqual(len(c.allocated_torque_packet(m,sign,out[m],PLAN)),20)
        c(sample(.010),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'missing_after_two_cycle_warmup'):
            c(sample(.015),{0:0.,1:0.},PLAN)

    def test_same_ending_gains_other_guard_values_and_inert_default(self):
        ending=with_gains(OLD,dict(gains(OLD),pitch_d=.085))
        self.assertEqual({k for k in set(ending)|set(PLAN) if ending.get(k)!=PLAN.get(k)},
                         {'name','duration_s','active_message','use_output_encoder_velocity'})
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def fixture(self,bad=False):
        class Cue:
            def __init__(self):self.off=False
            def tick(self):pass
            def check(self):pass
            def deactivate(self):self.off=True
        bus=Bus(timeout=True);report={};cue=Cue();counts={0:0,1:0}
        ch=TuningChannel(gains(PLAN),now=bus.now)
        def exchange(mid):
            original=bus.exchange(mid)
            def wrapped(packet,phase):
                row=original(packet,phase);row['feedback_received_monotonic']=bus.now()
                row['absolute_output_rad']=0.
                if phase==PLAN['control_phase']:
                    counts[mid]+=1
                    if bad and mid==1 and counts[mid]==10:row['absolute_output_rad']=1.
                return row
            return wrapped
        run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=OutputVelocityLiveController(ch),travel_factory=HoldTravel,indicator=cue)
        return bus,report,ch,cue

    def test_bounded_warmup_then_output_feedback_and_complete_stop(self):
        b,r,ch,cue=self.fixture()
        self.assertEqual(r['status'],'PASS',r.get('reason'))
        self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
        samples=r['samples']
        self.assertEqual(sum(s['attitude']['output_velocity_input']['warmup_rotor_proxy'] for s in samples),2)
        self.assertTrue(ch.status()['output_encoder_ready'])
        self.assertEqual(ch.status()['phase'],'STOPPED')

    def test_bad_output_channel_stops_both_and_never_rearms(self):
        b,r,ch,cue=self.fixture(bad=True)
        self.assertEqual(r['reason'],'output_encoder_inconsistent_step')
        self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
        stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
