import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_two_deck_heading import frame
from test_wheel_check import Bus
from two_deck_position_hold import PositionHoldController
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_trim_position_return import PLAN,main
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


class CurrentPositionTests(unittest.TestCase):
    def test_minute_entry_changes_only_duration_and_metadata(self):
        from two_deck_trim_position_observe import PLAN as MINUTE,main as minute_main
        changed={k for k in set(PLAN)|set(MINUTE) if PLAN.get(k)!=MINUTE.get(k)}
        self.assertEqual(changed,{'name','duration_s','control_phase','active_message'})
        self.assertEqual(MINUTE['duration_s'],60.)
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(minute_main([]),0)

    def test_default_inert_and_selected_inner_gains_guards_preserved(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        metadata={'name','active_message','control_phase'}
        self.assertEqual({k:v for k,v in BASE.items() if k not in metadata},
                         {k:PLAN[k] for k in BASE if k not in metadata})
        self.assertEqual(set(PLAN)-set(BASE),{'allow_position_velocity_target',
                         'position_speed_kp_per_s','position_speed_limit_m_s'})

    def test_zero_common_error_keeps_exact_selected_motor_packets(self):
        c=PositionHoldController();before=VelocityDiagnosticsController()
        for i in range(1,100):
            a=frame(i*.005,{0:100.+i*.001,1:-200.-i*.001})
            a['pitch_deg']=math.sin(i*.1)*.8;a['pitch_error_deg']=a['pitch_deg']
            a['pitch_rate_dps']=math.cos(i*.1)*16.
            b=copy.deepcopy(a);speeds={0:.2,1:-.1}
            out=c(a,speeds,PLAN);old=before(b,speeds,BASE)
            self.assertAlmostEqual(a['position_velocity_target_m_s'],0.)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(c.allocated_torque_packet(mid,sign,out[mid],PLAN),
                                 before.allocated_torque_packet(mid,sign,old[mid],BASE))

    def test_position_return_target_sign_cap_and_original_torque_budget(self):
        for displacement in (-.30,-.01,.01,.30):
            c=PositionHoldController();c(frame(.005,{0:10.,1:-20.}),{0:0.,1:0.},PLAN)
            a=frame(.01,{0:10.+displacement/.04,1:-20.+displacement/.04})
            out=c(a,{0:2.,1:2.},PLAN)
            self.assertLess(a['position_velocity_target_m_s']*displacement,0.)
            self.assertLessEqual(abs(a['position_velocity_target_m_s']),.01)
            self.assertLessEqual(abs(a['speed_pitch_reference_deg']),3.)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(len(c.allocated_torque_packet(mid,sign,out[mid],PLAN)),20)
                self.assertLessEqual(abs(c.allocations[mid].feedforward_nm),.12)
                self.assertLessEqual(abs(c.allocations[mid].predicted_net_nm),.12)

    def test_missing_position_feedback_still_rejects_before_command(self):
        c=PositionHoldController();a=frame(.005,{0:0.,1:0.});a.pop('wheel_position_forward_rad')
        with self.assertRaisesRegex(Fault,'position_hold_requires_both_encoders'):
            c(a,{0:0.,1:0.},PLAN)
        self.assertEqual(c.allocations,{})

    def test_full_runner_stops_both_and_never_rearms_after_display_failure(self):
        for fail in (False,True):
            b=Bus(timeout=True);report={};cue=Indicator(b,fail)
            def tick():cue.check();cue.ticks+=1
            cue.tick=tick
            def exchange(mid):
                original=b.exchange(mid)
                def call(packet,phase):
                    row=original(packet,phase)
                    row['feedback_received_monotonic']=b.now()
                    return row
                return call
            run({m:exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),report,True,
                now=b.now,sleep=b.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=PositionHoldController(),travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(report['status'],'FAIL' if fail else 'PASS',report.get('reason'))
            self.assertTrue(report['final_disabled_verified']);self.assertTrue(cue.off)
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
