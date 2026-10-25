import copy
from contextlib import redirect_stdout
import io
import math
import struct
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains
from protocol import RATIO
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample,checked_pair
from test_wheel_check import Bus
from two_deck_native_causal_balance import NativeCausalBalanceController
from two_deck_native_observed_balance import PLAN as BASE
from two_deck_native_smooth_balance import PLAN,NativeSmoothBalanceController,main


class NativeSmoothTests(unittest.TestCase):
    def controller(self):return NativeSmoothBalanceController(TuningChannel(gains(PLAN)))

    def test_default_inert_and_guard_changes_forbidden(self):
        self.assertEqual({k for k in set(PLAN)|set(BASE) if PLAN.get(k)!=BASE.get(k)},
            {'name','duration_s','common_net_slew_nm_s','control_phase','active_message'})
        self.assertEqual(gains(PLAN),gains(BASE))
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_steps_have_bounded_slew_no_windup_and_first_command_unchanged(self):
        c=self.controller();previous=None
        for i,value in enumerate([.03]*5+[.08]*10+[-.08]*20+[2.]*30+[-2.]*30):
            a=dict(t=(i+1)*.005)
            out,limited=c.shape_common_net_request(value,a,PLAN)
            if previous is None:self.assertEqual(out,.03)
            else:self.assertLessEqual(abs(out-previous),.010000000001)
            self.assertLessEqual(abs(out),.12+1e-12);previous=out
        self.assertAlmostEqual(out,-.12)
        self.assertTrue(limited)

    def test_invalid_limits_or_clock_do_not_allocate_packets(self):
        for value in [None,True,0.,3.,float('nan')]:
            c=self.controller()
            with self.assertRaises(Fault):
                c.shape_common_net_request(.01,dict(t=.005),dict(PLAN,common_net_slew_nm_s=value))
        c=self.controller();c.shape_common_net_request(0.,dict(t=.005),PLAN)
        with self.assertRaises(Fault):c.shape_common_net_request(.01,dict(t=.005),PLAN)

    def test_ramped_requests_keep_wire_budgets_parent_telemetry_and_saturation(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0])
        c=NativeSmoothBalanceController(ch);previous=None;limited=0
        for i in range(1,1601):
            clock[0]=i*.005;a=sample(clock[0])
            a.update(pitch_deg=.8*math.sin(60*clock[0]),pitch_error_deg=.8*math.sin(60*clock[0]))
            speeds={0:.01,1:-.01};commands=c(a,speeds,PLAN)
            s=a['net_command_slew'];limited+=s['slew_limited']
            if previous is not None:self.assertLessEqual(abs(s['common_output_nm']-previous),.010000000001)
            previous=s['common_output_nm']
            if s['slew_limited']:self.assertTrue(c.previous_limited)
            for m,sign in [(0,1),(1,-1)]:
                p=c.allocated_torque_packet(m,sign,commands[m],PLAN)
                ff,v,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
                self.assertEqual((pos,kp),(0,0))
                net=sign*ff*RATIO/256000.+kd*RATIO**2/128000000.*(sign*v*math.tau/(RATIO*2.56)-speeds[m])
                self.assertLessEqual(abs(net),.12+1e-12)
            c.observe_pair(checked_pair(a))
        self.assertGreater(limited,0)
        state=ch.status()
        for key in ['control_terms','command_slew','stationary_integral_growth_limited',
                    'position_error_proxy_m','selected_control_velocity_proxy_m_s']:
            self.assertIn(key,state)

    def test_slow_input_retains_exact_native_wire_packets(self):
        c=self.controller();prior=NativeCausalBalanceController(TuningChannel(gains(BASE)))
        for i in range(1,1401):
            a=sample(i*.005);a.update(pitch_deg=.2,pitch_error_deg=.2,pitch_rate_dps=0.)
            b=copy.deepcopy(a);out=c(a,{0:0.,1:0.},PLAN);old=prior(b,{0:0.,1:0.},BASE)
            for m,sign in [(0,1),(1,-1)]:
                self.assertEqual(c.allocated_torque_packet(m,sign,out[m],PLAN),
                    prior.allocated_torque_packet(m,sign,old[m],BASE))

    def test_fault_mode_zero_no_automatic_rearm(self):
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase'])
            c=NativeSmoothBalanceController(TuningChannel(gains(PLAN),now=bus.now));report={}
            class Cue:
                def check(self):pass
                def tick(self):pass
                def deactivate(self):pass
            def exchange(m):
                call=bus.exchange(m)
                def wrapped(packet,phase):
                    row=call(packet,phase);row['feedback_received_monotonic']=bus.now();return row
                return wrapped
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(PLAN,duration_s=.5),
                controller=c,travel_factory=HoldTravel,indicator=Cue())
            self.assertEqual(report['status'],'FAIL' if fail else 'PASS',report.get('reason'))
            self.assertTrue(report['final_disabled_verified'])
            stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[stop:]))
            with self.assertRaises(Fault):c.reset()


if __name__=='__main__':unittest.main()
