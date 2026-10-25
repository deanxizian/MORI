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
from two_deck_native_damping_balance import NativeDampingBalanceController
from two_deck_native_rate_compensation import PLAN,NativeRateCompensationController,main


class NativeRateCompensationTests(unittest.TestCase):
    def test_inert_default_and_trial100_gains_with_original_guards(self):
        from two_deck_native_damping_balance import PLAN as base
        self.assertEqual({k for k in set(PLAN)|set(base) if PLAN.get(k)!=base.get(k)},
            {'name','ap_kp','native_rate_compensation_fraction','control_phase','active_message'})
        self.assertEqual(gains(PLAN),dict(pitch_p=3.,pitch_i=.6,pitch_d=.05,speed_p=.25))
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_outer_loop_preserved_and_shaft_rate_term_opposes_both_directions(self):
        base={k:v for k,v in PLAN.items() if k!='native_rate_compensation_fraction'}
        c=NativeRateCompensationController(TuningChannel(gains(PLAN)))
        prior=NativeDampingBalanceController(TuningChannel(gains(base)))
        for i in range(1,1601):
            t=i*.005;a=sample(t);a.update(pitch_deg=.2+.1*math.sin(t),pitch_error_deg=.2+.1*math.sin(t))
            b=copy.deepcopy(a);speeds={0:.04*math.sin(3*t),1:-.05*math.cos(3*t)}
            c(a,speeds,PLAN);prior(b,speeds,base)
            for key in ['p_nm','i_nm','d_nm','desired_pitch_forward_deg']:
                self.assertEqual(a['ardupilot_balance'][key],b['ardupilot_balance'][key])
            info=a['native_rate_compensation']
            for m,speed in speeds.items():
                original=b['ardupilot_balance']['requested_net_per_wheel_nm'][m]
                self.assertEqual(info['before_per_wheel_nm'][m],original)
                self.assertAlmostEqual(info['after_per_wheel_nm'][m],
                    original-info['retained_shaft_damping_nm_per_rad_s']*speed)
                self.assertLessEqual(info['damping_per_wheel_nm'][m]*speed,0.)

    def test_zero_rate_same_wire_and_moving_rate_exact_budget_and_reference(self):
        for speed in [0.,-.3,.3,-5.,5.]:
            c=NativeRateCompensationController(TuningChannel(gains(PLAN)))
            base={k:v for k,v in PLAN.items() if k!='native_rate_compensation_fraction'}
            prior=NativeDampingBalanceController(TuningChannel(gains(base)))
            a=sample(.005);b=copy.deepcopy(a);speeds={0:speed,1:-speed}
            out=c(a,speeds,PLAN);old=prior(b,speeds,base)
            for m,sign in [(0,1),(1,-1)]:
                packet=c.allocated_torque_packet(m,sign,out[m],PLAN)
                ff,v,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
                self.assertEqual((pos,kp),(0,0))
                exact_kd=kd*RATIO**2/128000000.
                ff_nm=sign*ff*RATIO/256000.;target=sign*v*math.tau/(RATIO*2.56)
                net=ff_nm+exact_kd*(target-speeds[m])
                self.assertLessEqual(abs(net),.12+1e-12);self.assertLessEqual(abs(ff_nm),.12+1e-12)
                self.assertLessEqual(abs(target),6.)
                if speed==0.:self.assertEqual(packet,prior.allocated_torque_packet(m,sign,old[m],base))
                if abs(speed)==.3:
                    original=a['native_rate_compensation']['before_per_wheel_nm'][m]
                    expected=.75*speeds[m]+original/exact_kd
                    self.assertLessEqual(abs(target-expected),math.tau/(RATIO*2.56)/2+1e-12)

    def test_invalid_compensation_rejects_without_packet_allocation(self):
        for fraction in [None,True,float('nan'),0.,1.,.8]:
            c=NativeRateCompensationController(TuningChannel(gains(PLAN)))
            with self.assertRaises(Fault):c(sample(.005),{0:0.,1:0.},dict(PLAN,native_rate_compensation_fraction=fraction))
            self.assertFalse(c.native_allocations)
        c=NativeRateCompensationController(TuningChannel(gains(PLAN)))
        with self.assertRaises(Fault):c(sample(.005),{0:6.1,1:0.},PLAN)
        self.assertFalse(c.native_allocations)

    def test_lifecycle_duration_and_fault_stop_both_no_rearm(self):
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase'])
            c=NativeRateCompensationController(TuningChannel(gains(PLAN),now=bus.now));report={}
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


if __name__=='__main__':raise SystemExit(unittest.main())
