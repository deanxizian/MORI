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
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_native_damping_stronger import PLAN,StrongerNativeDampingController,main


class StrongerDampingTests(unittest.TestCase):
    def test_default_inert_and_exact_wire_budget_and_label(self):
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        for speed in [-5.,-.3,0.,.3,5.]:
            c=StrongerNativeDampingController(TuningChannel(gains(PLAN)))
            a=sample(.005);speeds={0:speed,1:-speed};out=c(a,speeds,PLAN)
            for m,sign in [(0,1),(1,-1)]:
                p=c.allocated_torque_packet(m,sign,out[m],PLAN)
                ff,v,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
                self.assertEqual((p[2]&0x70,pos,kp),(0x10,0,0))
                self.assertEqual(kd,math.floor(.16/(RATIO**2/128000000.)))
                exact_kd=kd*RATIO**2/128000000.
                net=sign*ff*RATIO/256000.+exact_kd*(sign*v*math.tau/(RATIO*2.56)-speeds[m])
                self.assertLessEqual(abs(net),.12+1e-12)
                self.assertLessEqual(abs(sign*ff*RATIO/256000.),.12+1e-12)
                self.assertLessEqual(abs(v*math.tau/(RATIO*2.56)),6.)
            a['elapsed_s']=.005
            self.assertEqual(c.extra_telemetry(dict(attitude=a))['native_execution_kd'],.16)

    def test_end_and_feedback_fault_disable_both_without_rearm(self):
        for fail in [False,True]:
            b=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase'])
            c=StrongerNativeDampingController(TuningChannel(gains(PLAN),now=b.now));r={}
            class Cue:
                def check(self):pass
                def tick(self):pass
                def deactivate(self):pass
            def exchange(m):
                call=b.exchange(m)
                def wrapped(packet,phase):
                    row=call(packet,phase);row['feedback_received_monotonic']=b.now();return row
                return wrapped
            run({m:exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),r,True,
                now=b.now,sleep=b.sleep,display=lambda _:None,plan=dict(PLAN,duration_s=.5),
                controller=c,travel_factory=HoldTravel,indicator=Cue())
            self.assertEqual(r['status'],'FAIL' if fail else 'PASS',r.get('reason'))
            self.assertTrue(r['final_disabled_verified'])
            stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))
            with self.assertRaises(Fault):c.reset()


if __name__=='__main__':raise SystemExit(unittest.main())
