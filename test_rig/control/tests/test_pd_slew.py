import copy
from contextlib import redirect_stdout
import io
import math
import tempfile
import unittest
from unittest.mock import patch
from air_trial import run
from ardupilot_balance_core import BalancePitchPID
from ardupilot_slew import SlewLimiter
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains,with_gains,validate_plan_change
from pd_slew_oracle import build,calculate
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_pd_slew import PLAN,PDSlewLiveController,main
from two_deck_live_stationary_integral import PLAN as OLD


class PDSlewParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.binary=build(cls.temp.name)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_combined_pid_matches_unmodified_upstream_functions(self):
        for smax in (0.,2.,16.6666666667):
            config=dict(kp=3.25/.12,ki=.6/.12,kd=.070/.12,imax=.02/.12,
                fltt=0.,flte=0.,fltd=10.,ff=.02,dff=.001,pitch_ff=.1,
                pitch_max=math.radians(5),limit_tc=.5,limit_threshold=.6,smax=smax,slew_tau=1.)
            rows=[]
            for i in range(2400):
                t=i*.005
                target=.02*math.sin(math.tau*.7*t)
                actual=.015*math.sin(math.tau*11.*t)+.01*math.sin(math.tau*.9*t)
                if 1000<=i<1040:actual+=.06
                rows.append((target,actual,.005,i%71<5,i==0))
            reference=calculate(self.binary,config,rows);port=BalancePitchPID(**config)
            self.assertEqual(len(reference),len(rows))
            minimum=1.
            for i,(row,wanted) in enumerate(zip(rows,reference)):
                target,actual,dt,limit,_=row
                output=port.update(target,actual,dt,limit,now_ms=1000+(i+1)*5)
                z=port.info
                got=[output,z['p'],z['i'],z['d'],z['ff'],z['error_rad'],z['target_rad'],
                     z['pitch_low_rad'],z['pitch_high_rad'],z.get('pd_slew_modifier',1.),
                     z.get('pd_slew_rate_output_per_s',0.)]
                for k,(a,b) in enumerate(zip(got,wanted)):
                    # Disabled Python path intentionally omits the unused
                    # shadow slew filter to preserve the prior inert port.
                    if smax==0 and k==10:continue
                    self.assertAlmostEqual(a,b,delta=8e-4 if k==10 else 5e-5,msg=f'field{k},frame{i},smax{smax}')
                minimum=min(minimum,z.get('pd_slew_modifier',1.))
            if smax:self.assertLess(minimum,.9)


class PDSlewSafetyTests(unittest.TestCase):
    def test_live_gain_update_preserves_pid_and_slew_filter_states(self):
        c=PDSlewLiveController(TuningChannel(gains(PLAN)))
        for i in range(1,301):
            t=i*.005;a=sample(t);a.update(pitch_deg=math.sin(math.tau*11*t),
                pitch_error_deg=math.sin(math.tau*11*t),pitch_rate_dps=50*math.cos(math.tau*11*t))
            c(a,{0:0.,1:0.},PLAN)
        pid=c.pid;slew=pid.slew;before=copy.deepcopy(slew.__dict__)
        filters={k:v for k,v in pid.__dict__.items() if k not in ('kp','ki','kd','slew')}
        updated=with_gains(PLAN,dict(gains(PLAN),pitch_p=3.))
        c.apply_live_gains(PLAN,updated)
        self.assertIs(c.pid,pid);self.assertIs(c.pid.slew,slew)
        self.assertEqual(before,slew.__dict__)
        self.assertEqual(filters,{k:v for k,v in pid.__dict__.items() if k not in ('kp','ki','kd','slew')})

    def test_only_pd_scaled_i_unchanged_and_local_floor_explicit(self):
        config=dict(kp=25.,ki=5.,kd=.6,imax=.2,fltd=10.,limit_tc=0.)
        a=BalancePitchPID(**config,smax=.2,slew_min_modifier=.5)
        b=BalancePitchPID(**config)
        raw_min=1.
        for i in range(1000):
            value=.03*math.sin(i*.4);t=100000+i*5
            a.update(0.,value,.005,now_ms=t);b.update(0.,value,.005)
            z=a.info;factor=z['pd_slew_modifier'];raw_min=min(raw_min,z['pd_slew_raw_modifier'])
            self.assertGreaterEqual(factor,.5);self.assertLessEqual(factor,1.)
            self.assertEqual(z['i'],b.info['i']);self.assertEqual(z['error_rad'],b.info['error_rad'])
            self.assertAlmostEqual(z['p'],b.info['p']*factor)
            self.assertAlmostEqual(z['d'],b.info['d']*factor)
        self.assertLess(raw_min,.5)

    def test_invalid_inputs_and_uint32_clock_are_not_silent(self):
        for args in [(float('nan'),1.),(1.,0.),(-1.,1.)]:
            with self.assertRaises(ValueError):SlewLimiter(*args)
        s=SlewLimiter(1.,1.)
        for stamp in (None,-1,2**32,1.5):
            with self.assertRaises(ValueError):s.modifier(1.,.005,stamp)
        for stamp in (2**32-10,2**32-5,0,5):
            m=s.modifier(.01,.005,stamp);self.assertTrue(0<m<=1.)
        self.assertEqual(s.modifier(1.,0.,10),1.)

    def test_inert_default_and_existing_motor_guards_unchanged(self):
        ending=with_gains(OLD,dict(gains(OLD),pitch_d=.070))
        self.assertEqual({k for k in set(ending)|set(PLAN) if ending.get(k)!=PLAN.get(k)},
            {'name','active_message','allow_pd_slew_modifier','ap_smax','ap_slew_tau_s','ap_slew_min_modifier'})
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        c=PDSlewLiveController(TuningChannel(gains(PLAN)))
        with self.assertRaisesRegex(Fault,'wheel_speed'):c(sample(.005),{0:7.,1:0.},PLAN)
        c=PDSlewLiveController(TuningChannel(gains(PLAN)))
        with self.assertRaisesRegex(Fault,'outside_experimental'):
            c(sample(.005),{0:0.,1:0.},dict(PLAN,ap_slew_min_modifier=.1))
        with self.assertRaises(ValueError):validate_plan_change(PLAN,dict(PLAN,ap_smax=1.))

    def fixture(self,fault=False):
        class Cue:
            def __init__(self):self.off=False
            def tick(self):pass
            def check(self):pass
            def deactivate(self):self.off=True
        bus=Bus(timeout=True);report={};cue=Cue();ch=TuningChannel(gains(PLAN),now=bus.now);count=[0]
        def exchange(mid):
            original=bus.exchange(mid)
            def wrapped(packet,phase):
                row=original(packet,phase);row['feedback_received_monotonic']=bus.now()
                if mid==1 and phase==PLAN['control_phase']:count[0]+=1
                return row
            return wrapped
        class IMU(HandIMU):
            def sample(self):
                s=super().sample()
                if fault and count[0]>=30:s['gyro_dps'][1]=500.
                return s
        run({m:exchange(m) for m in (0,1)},IMU(bus),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=PDSlewLiveController(ch),travel_factory=HoldTravel,indicator=cue)
        return bus,report,ch,cue

    def test_complete_mode1_run_and_final_verified_stop(self):
        b,r,ch,cue=self.fixture()
        self.assertEqual(r['status'],'PASS',r.get('reason'));self.assertTrue(r['final_disabled_verified'])
        self.assertTrue(cue.off);self.assertEqual(ch.status()['phase'],'STOPPED')
        self.assertIn('effective_pitch_p',ch.status())
        self.assertTrue(all(w['feedback']['mode']==1 for s in r['samples'] for w in s['wheels'].values()))

    def test_raw_fault_stops_both_without_rearm(self):
        b,r,ch,cue=self.fixture(True)
        self.assertEqual(r['status'],'FAIL');self.assertIn('rate',r['reason'])
        self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
        stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
