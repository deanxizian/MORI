import copy
from contextlib import redirect_stdout
import io,math,struct,unittest
from unittest.mock import patch
from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains,with_gains,validate_set,validate_plan_change,FIELDS
from protocol import RATIO
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample,checked_pair,request
from test_wheel_check import Bus
from two_deck_native_360_compare import PLAN as BASE
from two_deck_native_360_d_tuning import PLAN,NativeDampingController,main

class ExtendedDTests(unittest.TestCase):
    def test_only_envelope_extension_keeps_initial_gains_and_guard_rejections(self):
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
            {'name','control_phase','active_message'})
        self.assertEqual(gains(PLAN),dict(pitch_p=3.5,pitch_i=.6,pitch_d=.09,speed_p=.25))
        self.assertEqual(FIELDS['pitch_d'],('ap_kd',.050,.150,.015))
        with patch('socket.socket',side_effect=AssertionError('socket')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        ch=TuningChannel(gains(PLAN),session='d-envelope')
        for change in [dict(key='pitch_d',value=.151),dict(key='pitch_d',value=.106),dict(key='temperature_limit_c',value=85),dict(session='wrong')]:
            with self.assertRaises(ValueError):validate_set(dict(request(ch),**change),ch.session,0,gains(PLAN))
        for change in [dict(temperature_limit_c=85),dict(predicted_net_torque_limit_nm=.15),dict(wheel_speed_limit_rad_s=7),dict(pitch_limit_deg=35)]:
            with self.assertRaises(ValueError):validate_plan_change(PLAN,dict(PLAN,**change))

    def test_four_small_live_d_steps_preserve_pid_and_every_wire_budget(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0]);c=NativeDampingController(ch);pid=None
        updates={1201:(0,.105),2201:(1,.120),3201:(2,.135),4201:(3,.150)}
        for i in range(1,5401):
            clock[0]=i*.005
            if i in updates:
                rev,value=updates[i];self.assertEqual(ch.submit(request(ch,revision=rev,key='pitch_d',value=value,rid='d-step-'+str(rev)))['status'],'QUEUED')
            a=sample(clock[0]);out=c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            if pid is None:pid=c.pid
            self.assertIs(c.pid,pid)
            if i>1:self.assertFalse(a['ardupilot_balance']['filter_reset'])
            for mid,sign in [(0,1),(1,-1)]:
                packet=c.allocated_torque_packet(mid,sign,out[mid],PLAN)
                ff,rate,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
                self.assertEqual((pos,kp),(0,0))
                self.assertLessEqual(abs(ff*RATIO/256000.),.12+1e-12)
                self.assertLessEqual(abs(rate*math.tau/(RATIO*2.56)),6.)
                self.assertLessEqual(abs(c.native_allocations[mid].predicted_net_nm),.12+1e-12)
        self.assertEqual([e['status'] for e in c.events],['RAMP_STARTED','APPLIED']*4)
        self.assertEqual(ch.status()['current']['pitch_d'],.15)
        self.assertEqual(ch.status()['revision'],4)

    def test_high_d_saturation_and_fault_still_disable_both_without_rearm(self):
        high=with_gains(PLAN,dict(gains(PLAN),pitch_d=.15))
        c=NativeDampingController(TuningChannel(gains(high)))
        a=sample(.005);a.update(pitch_deg=4.,pitch_error_deg=4.)
        c(a,{0:1.,1:-1.},high)
        self.assertTrue(a['ardupilot_balance']['adapter_limited'])
        self.assertTrue(all(abs(x.predicted_net_nm)<=.12+1e-12 for x in c.native_allocations.values()))
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==high['control_phase']);r={};control=NativeDampingController(TuningChannel(gains(high),now=bus.now))
            class Cue:
                def check(self):pass
                def tick(self):pass
                def deactivate(self):pass
            def exchange(mid):
                f=bus.exchange(mid)
                def call(p,phase):
                    row=f(p,phase);row['feedback_received_monotonic']=bus.now();return row
                return call
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),r,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(high,duration_s=.5),
                controller=control,travel_factory=HoldTravel,indicator=Cue())
            self.assertEqual(r['status'],'FAIL' if fail else 'PASS',r.get('reason'));self.assertTrue(r['final_disabled_verified'])
            stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[stop:]))
            with self.assertRaisesRegex(Fault,'cannot_reset'):control.reset()
if __name__=='__main__':unittest.main()
