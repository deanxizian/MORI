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
from two_deck_native_observed_balance import PLAN as BASE,NativeObservedBalanceController
from two_deck_native_damping_balance import PLAN,NativeDampingBalanceController,main


class NativeDampingTests(unittest.TestCase):
    def test_default_inert_and_only_execution_comparison_changes(self):
        self.assertEqual({k for k in set(PLAN)|set(BASE) if PLAN.get(k)!=BASE.get(k)},
            {'name','duration_s','native_execution_kd','control_phase','active_message'})
        self.assertEqual(gains(PLAN),gains(BASE))
        self.assertNotIn('common_net_slew_nm_s',PLAN)
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_original_outer_requests_no_host_slew_and_exact_wire_budgets(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0])
        c=NativeDampingBalanceController(ch);prior=NativeObservedBalanceController(TuningChannel(gains(BASE)))
        for i in range(1,1601):
            clock[0]=i*.005;a=sample(clock[0]);a.update(
                pitch_deg=.2+.3*math.sin(30*clock[0]),pitch_error_deg=.2+.3*math.sin(30*clock[0]))
            b=copy.deepcopy(a);speeds={0:.03,1:-.025}
            out=c(a,speeds,PLAN);prior(b,speeds,BASE)
            for key in ['p_nm','i_nm','d_nm','requested_net_per_wheel_nm','desired_pitch_forward_deg']:
                self.assertEqual(a['ardupilot_balance'][key],b['ardupilot_balance'][key])
            self.assertEqual(a['ardupilot_balance']['requested_net_nm'],a['ardupilot_balance']['pid_requested_net_nm'])
            self.assertNotIn('net_command_slew',a)
            for mid,sign in [(0,1),(1,-1)]:
                p=c.allocated_torque_packet(mid,sign,out[mid],PLAN)
                ff,v,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
                self.assertEqual((pos,kp),(0,0))
                damping=kd*RATIO**2/128000000.
                self.assertGreater(damping,.079);self.assertLessEqual(damping,.080)
                net=sign*ff*RATIO/256000.+damping*(sign*v*math.tau/(RATIO*2.56)-speeds[mid])
                self.assertLessEqual(abs(net),.12+1e-12)
                self.assertLessEqual(abs(sign*ff*RATIO/256000.),.12+1e-12)
                self.assertLessEqual(abs(v*math.tau/(RATIO*2.56)),6.)
            c.observe_pair(checked_pair(a))
        for key in ['native_execution_kd','control_terms','stationary_integral_growth_limited',
                    'position_error_proxy_m','selected_control_velocity_proxy_m_s']:
            self.assertIn(key,ch.status())

    def test_native_damping_cannot_change_mid_cycle_and_fault_clears_allocations(self):
        c=NativeDampingBalanceController(TuningChannel(gains(PLAN)))
        a=sample(.005);out=c(a,{0:0.,1:0.},PLAN)
        with self.assertRaises(Fault):c.allocated_torque_packet(0,1,out[0],dict(PLAN,native_execution_kd=.04))
        with self.assertRaises(Fault):c(sample(.01),{0:6.1,1:0.},PLAN)
        self.assertFalse(c.native_allocations)

    def test_fault_and_duration_stop_both_wheels_without_rearm(self):
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase'])
            c=NativeDampingBalanceController(TuningChannel(gains(PLAN),now=bus.now));report={}
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
