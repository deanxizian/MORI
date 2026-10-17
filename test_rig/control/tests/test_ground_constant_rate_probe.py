import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import math
import struct
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from ground_constant_rate_probe import PLAN,ConstantRateProbe,desired_rate,main
from protocol import RATIO,crc32_words
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus


class GroundConstantRateTests(unittest.TestCase):
    def test_inert_default_and_explicit_profile(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),patch(
                'socket.socket',side_effect=AssertionError('socket I/O')),redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):main(['--run-ground-constant-rate-probe'])
        for t,stage,value in [(0,'forward',0),(.2,'forward',.1),(.4,'forward',.2),
                (3.6,'forward',.2),(3.8,'forward',.1),(4.,'pause',0),
                (4.5,'reverse',0),(4.9,'reverse',-.2),(8.3,'reverse',-.1),(8.5,'final_zero',0),(9.,'final_zero',0)]:
            s,v=desired_rate(t);self.assertEqual(s,stage);self.assertAlmostEqual(v,value)

    def test_wire_direction_zero_ff_stiffness_and_sampled_budgets(self):
        c=ConstantRateProbe()
        for i in range(1801):
            a=sample(1+i*.005);speeds={0:.2*math.sin(i*.01),1:.15*math.sin(i*.01)}
            commands=c(a,speeds,PLAN);self.assertEqual(commands,{0:0.,1:0.})
            raws=[]
            for mid,sign in ((0,1),(1,-1)):
                p=c.allocated_torque_packet(mid,sign,0.,PLAN)
                ff,v,pos,kp,kd=struct.unpack_from('<hhihh',p,4);raws.append(v)
                self.assertEqual((ff,pos,kp),(0,0,0))
                self.assertEqual(struct.unpack_from('<I',p,16)[0],crc32_words(p[:16]))
                allocation=c.allocations[mid]
                self.assertLessEqual(abs(allocation.predicted_net_nm),.08+1e-12)
                self.assertLessEqual(abs(v*math.tau/(RATIO*2.56)),.2+1e-12)
                self.assertLessEqual(kd*RATIO**2/128000000,1.2)
            self.assertEqual(raws[0],-raws[1])
            self.assertNotIn('ardupilot_balance',a)
        with self.assertRaisesRegex(Fault,'cannot_reset'):c.reset()

    def fixture(self,mutation=None):
        class Cue:
            def __init__(self):self.off=False;self.ticks=0
            def check(self):pass
            def tick(self):self.ticks+=1
            def deactivate(self):self.off=True
        b=Bus(timeout=True);r={};cue=Cue();controller=ConstantRateProbe()
        def exchange(mid):
            original=b.exchange(mid)
            def call(p,phase):
                row=original(p,phase);row['feedback_received_monotonic']=b.now()
                # Older bus fixture predates the independent output field.
                # This is deterministic harness data, not a motor model.
                row.setdefault('absolute_output_rad',row['position_rad']%math.tau)
                if mutation and phase==PLAN['control_phase'] and mid==1:mutation(row)
                return row
            return call
        run({m:exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),r,True,
            now=b.now,sleep=b.sleep,display=lambda _:None,plan=PLAN,
            controller=controller,travel_factory=HoldTravel,indicator=cue)
        return b,r,controller,cue

    def test_complete_sequence_and_final_disabled_no_balance_claim(self):
        b,r,c,cue=self.fixture()
        self.assertEqual(r['status'],'PASS',r.get('reason'))
        self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
        self.assertEqual(c.checked_stages,{'forward','pause','reverse','final_zero'})
        self.assertEqual(c.summary()['loaded_smoothness'],'NOT_TESTED')
        self.assertEqual(c.summary()['balanced_operation'],'NOT_APPLICABLE')
        active=[p for _,p,phase in b.log if phase==PLAN['control_phase']]
        self.assertTrue(any(struct.unpack_from('<h',p,6)[0]>0 for p in active))
        self.assertTrue(any(struct.unpack_from('<h',p,6)[0]<0 for p in active))

    def test_faults_stop_both_and_never_rearm(self):
        for field,value in [('speed_rad_s',.61),('temperature_c',70),
                            ('absolute_output_rad',1.5),('errors_raw',1)]:
            with self.subTest(field=field):
                # Output jump after at least one accepted pair, so an origin
                # cannot swallow the bad sample.
                calls=[0]
                def mutation(row):
                    calls[0]+=1
                    if calls[0]>=10:row[field]=value
                b,r,c,cue=self.fixture(mutation)
                self.assertEqual(r['status'],'FAIL');self.assertTrue(r['final_disabled_verified'])
                self.assertTrue(cue.off)
                k=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
                self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[k:]))

    def test_raw_guard_precedence_and_failure_latch(self):
        for a,speeds in [(dict(sample(1),pitch_deg=13.),{0:0.,1:0.}),
                         (sample(1),{0:.61,1:0.})]:
            c=ConstantRateProbe()
            with self.assertRaises(Fault):c(a,speeds,PLAN)
            with self.assertRaisesRegex(Fault,'fault_latched'):c(sample(1.005),{0:0.,1:0.},PLAN)


if __name__=='__main__':unittest.main()
