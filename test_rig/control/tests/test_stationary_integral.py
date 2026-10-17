import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch
from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import LiveTuningController,TuningChannel
from live_tuning_policy import gains,with_gains
from stationary_integral import StationaryIntegralGate,StationaryIntegralLiveController
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_stationary_integral import PLAN,main
from two_deck_live_tuning_temp80 import PLAN as OLD


class StationaryIntegralTests(unittest.TestCase):
    def test_dwell_hysteresis_and_immediate_disturbance_exit(self):
        g=StationaryIntegralGate()
        for i in range(20):self.assertFalse(g.update(i*.005,.1,.1,{0:0.,1:0.}))
        self.assertTrue(g.update(.1,.1,.1,{0:0.,1:0.}))
        self.assertTrue(g.update(.105,.6,1.,{0:.04,1:0.}))
        self.assertFalse(g.update(.110,.1,1.5,{0:0.,1:0.}))
        self.assertFalse(g.update(.115,.1,.1,{0:0.,1:0.}))
        for field in ('rate','wheel','angle'):
            x=StationaryIntegralGate();x.limited=True
            self.assertFalse(x.update(1.,.75 if field=='angle' else 0.,
                1.5 if field=='rate' else 0.,{0:.06 if field=='wheel' else 0.,1:0.}))
        with self.assertRaises(Fault):g.update(.114,0.,0.,{0:0.,1:0.})
        with self.assertRaises(Fault):StationaryIntegralGate().update(1.,float('nan'),0.,{0:0.,1:0.})

    def test_integral_stops_growing_but_p_d_and_unwinding_remain(self):
        c=StationaryIntegralLiveController(TuningChannel(gains(PLAN)))
        def step(t,pitch):
            a=sample(t);a.update(pitch_deg=pitch,pitch_error_deg=pitch,pitch_rate_dps=0.)
            out=c(a,{0:0.,1:0.},PLAN)
            for m in out:
                self.assertLessEqual(abs(c.allocations[m].feedforward_nm),.12)
                self.assertLessEqual(abs(c.allocations[m].predicted_net_nm),.12)
            return a
        for i in range(1,100):a=step(i*.005,.4)
        held=a['ardupilot_balance']['i_nm']
        self.assertTrue(a['stationary_integrator']['growth_limited'])
        self.assertGreater(abs(a['ardupilot_balance']['p_nm']),0.)
        self.assertEqual(step(.5,.4)['ardupilot_balance']['i_nm'],held)
        a=step(.505,0.)
        self.assertLess(abs(a['ardupilot_balance']['i_nm']),abs(held))
        self.assertGreater(abs(a['ardupilot_balance']['d_nm']),0.)
        a=step(.510,1.1)
        self.assertFalse(a['stationary_integrator']['growth_limited'])
        self.assertFalse(a['ardupilot_balance']['motor_limit'])

    def test_moving_input_exactly_matches_original_packets(self):
        c=StationaryIntegralLiveController(TuningChannel(gains(PLAN)))
        old=with_gains(OLD,dict(gains(OLD),pitch_d=.085))
        b=LiveTuningController(TuningChannel(gains(old)))
        for i in range(1,300):
            a=sample(i*.005);a['pitch_rate_dps']=2.;z=copy.deepcopy(a)
            speeds={0:.1,1:.11}
            ca=c(a,speeds,PLAN);cb=b(z,speeds,old)
            self.assertEqual(ca,cb)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(c.allocated_torque_packet(mid,sign,ca[mid],PLAN),
                                 b.allocated_torque_packet(mid,sign,cb[mid],old))

    def test_default_inert_and_guard_settings_unchanged(self):
        old=with_gains(OLD,dict(gains(OLD),pitch_d=.085))
        self.assertEqual({k for k in set(old)|set(PLAN) if old.get(k)!=PLAN.get(k)},
                         {'name','duration_s','active_message','stationary_integral_guard'})
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        c=StationaryIntegralLiveController(TuningChannel(gains(PLAN)))
        with self.assertRaisesRegex(Fault,'wheel_speed'):c(sample(.005),{0:7.,1:0.},PLAN)

    def fixture(self,fault=False):
        class Cue:
            def __init__(self):self.off=False
            def tick(self):pass
            def check(self):pass
            def deactivate(self):self.off=True
        bus=Bus(timeout=True);report={};cue=Cue();ch=TuningChannel(gains(PLAN),now=bus.now)
        active_pairs=[0]
        def exchange(mid):
            original=bus.exchange(mid)
            def wrapped(packet,phase):
                row=original(packet,phase);row['feedback_received_monotonic']=bus.now()
                if mid==1 and phase==PLAN['control_phase']:active_pairs[0]+=1
                return row
            return wrapped
        class IMU(HandIMU):
            def sample(self):
                s=super().sample()
                if fault and active_pairs[0]>=30:s['gyro_dps'][1]=500.
                return s
        run({m:exchange(m) for m in (0,1)},IMU(bus),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=StationaryIntegralLiveController(ch),travel_factory=HoldTravel,indicator=cue)
        return bus,report,ch,cue

    def test_run_keeps_mode1_until_verified_final_stop(self):
        b,r,ch,cue=self.fixture()
        self.assertEqual(r['status'],'PASS',r.get('reason'))
        self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
        self.assertTrue(any(s['attitude']['stationary_integrator']['growth_limited'] for s in r['samples']))
        self.assertTrue(all(w['feedback']['mode']==1 for s in r['samples'] for w in s['wheels'].values()))
        self.assertEqual(ch.status()['phase'],'STOPPED')

    def test_fault_stops_both_without_rearm(self):
        b,r,ch,cue=self.fixture(fault=True)
        self.assertEqual(r['status'],'FAIL');self.assertTrue(r['final_disabled_verified'])
        self.assertIn('rate',r['reason']);self.assertGreater(len(r['samples']),0)
        stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
