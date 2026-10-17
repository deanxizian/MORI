import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch

from attitude import Fault
from live_tuning import TuningChannel
from live_tuning_policy import FIELDS,gains,with_gains,validate_set,validate_plan_change
from test_live_tuning import sample,checked_pair,request
from two_deck_live_quiet_baseline import PLAN as BASE,PitchFramePositionReturnLiveController
from two_deck_live_lower_pitch_gain import PLAN,main


class LowerPitchGainTests(unittest.TestCase):
    def test_inert_one_factor_entry_and_preserved_guard_contract(self):
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
                         {'name','ap_kp','active_message'})
        self.assertEqual(gains(PLAN),dict(pitch_p=2.5,pitch_i=.6,pitch_d=.05,speed_p=.25))
        self.assertEqual(FIELDS['pitch_p'],('ap_kp',2.,3.5,.25))
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        for field,value in [('duration_s',1801),('temperature_limit_c',81),
                            ('native_wheel_damping_nm_per_rad_s',.01),
                            ('feedforward_torque_limit_nm',.13),('pitch_limit_deg',31)]:
            with self.assertRaises(ValueError):validate_plan_change(PLAN,dict(PLAN,**{field:value}))
        current=dict(gains(PLAN),pitch_p=2.25)
        ch=TuningChannel(current,session='bounds')
        self.assertEqual(validate_set(request(ch,value=2.),ch.session,0,current),('pitch_p',2.,2.))
        for value in [1.99,3.51,2.5+1e-6,float('nan'),True]:
            with self.assertRaises(ValueError):validate_set(request(ch,value=value),ch.session,0,current)

    def test_same_controller_wire_parity_and_unchanged_budgets(self):
        equivalent=with_gains(BASE,gains(PLAN))
        a=PitchFramePositionReturnLiveController(TuningChannel(gains(PLAN)))
        b=PitchFramePositionReturnLiveController(TuningChannel(gains(equivalent)))
        for i in range(1,1201):
            x=sample(i*.005);x.update(pitch_deg=.8*math.sin(i*.05),pitch_rate_dps=20.*math.cos(i*.05),
                wheel_position_forward_rad={0:.2*math.sin(i*.01),1:.2*math.sin(i*.01)})
            y=copy.deepcopy(x);speeds={0:.3*math.sin(i*.04),1:.2*math.cos(i*.03)}
            ca=a(x,speeds,PLAN);cb=b(y,speeds,equivalent)
            self.assertEqual(ca,cb)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(a.allocated_torque_packet(mid,sign,ca[mid],PLAN),
                                 b.allocated_torque_packet(mid,sign,cb[mid],equivalent))
                self.assertLessEqual(abs(a.allocations[mid].feedforward_nm),.12+1e-12)
                self.assertLessEqual(abs(a.allocations[mid].predicted_net_nm),.12+1e-12)

    def test_staged_lower_ramps_keep_pid_origin_and_filters_then_disarm_latches(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0])
        c=PitchFramePositionReturnLiveController(ch);pid=None;origin=None;trajectory=[]
        for i in range(1,2801):
            clock[0]=i*.005
            if i==1201:ch.submit(request(ch,value=2.25,rid='lower225'))
            if i==2201:ch.submit(request(ch,revision=1,value=2.,rid='lower200'))
            a=sample(clock[0]);a['wheel_position_forward_rad']={0:.01,1:.01}
            c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            if pid is None:pid=c.pid;origin=copy.deepcopy(c.position_origin)
            self.assertIs(c.pid,pid);self.assertEqual(c.position_origin,origin)
            if i>1:self.assertFalse(a['ardupilot_balance']['filter_reset'])
            trajectory.append(a['live_tuning']['current']['pitch_p'])
        self.assertAlmostEqual(trajectory[-1],2.)
        self.assertLessEqual(max(abs(y-x) for x,y in zip(trajectory,trajectory[1:])),.25*.005/2+1e-12)
        self.assertEqual([e['status'] for e in c.events],['RAMP_STARTED','APPLIED','RAMP_STARTED','APPLIED'])
        with self.assertRaises(Fault):c.reset()
        ch.disarm.set()
        with self.assertRaisesRegex(Fault,'disarm'):c(sample(14.005),{0:0.,1:0.},PLAN)


if __name__=='__main__':unittest.main()
