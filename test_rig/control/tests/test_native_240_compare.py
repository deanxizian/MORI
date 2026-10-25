import copy
from contextlib import redirect_stdout
import io
import math
import struct
import unittest
from unittest.mock import patch

from air_trial import run
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains
from protocol import RATIO
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_native_080_compare import PLAN as BASE
from two_deck_native_240_compare import PLAN,NativeDampingController,main


class Native240ComparisonTests(unittest.TestCase):
    def test_native_only_change_inert_default_exact_wire_and_guards(self):
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
            {'name','native_execution_kd','control_phase','active_message'})
        self.assertEqual(gains(PLAN),gains(BASE))
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        for speed in [-5.,-.3,0.,.3,5.]:
            c=NativeDampingController(TuningChannel(gains(PLAN)))
            a=sample(.005);speeds={0:speed,1:-speed};out=c(a,speeds,PLAN)
            for motor,sign in [(0,1),(1,-1)]:
                packet=c.allocated_torque_packet(motor,sign,out[motor],PLAN)
                ff,rate,position,kp,kd=struct.unpack_from('<hhihh',packet,4)
                self.assertEqual((packet[2]&0x70,position,kp),(0x10,0,0))
                self.assertEqual(kd,math.floor(.240/(RATIO**2/128000000.)))
                exact_kd=kd*RATIO**2/128000000.
                net=sign*ff*RATIO/256000.+exact_kd*(sign*rate*math.tau/(RATIO*2.56)-speeds[motor])
                self.assertLessEqual(abs(net),.12+1e-12)
                self.assertLessEqual(abs(ff*RATIO/256000.),.12+1e-12)
                self.assertLessEqual(abs(rate*math.tau/(RATIO*2.56)),6.)
            a['elapsed_s']=.005
            self.assertEqual(c.extra_telemetry(dict(attitude=a))['native_execution_kd'],.240)

    def test_finite_stop_and_feedback_fault_disable_both_no_rearm(self):
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase'])
            c=NativeDampingController(TuningChannel(gains(PLAN),now=bus.now));report={}
            class Cue:
                def check(self):pass
                def tick(self):pass
                def deactivate(self):pass
            def exchange(motor):
                call=bus.exchange(motor)
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
            with self.assertRaisesRegex(RuntimeError,'cannot_reset'):c.reset()


if __name__=='__main__':unittest.main()
