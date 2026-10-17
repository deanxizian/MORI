import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from ground_velocity_hold import VelocityHoldController
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_two_deck_heading import frame
from test_wheel_check import Bus
from two_deck_heading_hold import PLAN as BEFORE,RelativeHeadingController
from two_deck_position_hold import PLAN,PositionHoldController,main


class PositionHoldTests(unittest.TestCase):
    def test_inert_default_and_preserved_v88_inner_baseline(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        excluded={'name','active_message'}
        self.assertEqual({k:v for k,v in BEFORE.items() if k not in excluded},
                         {k:PLAN[k] for k in BEFORE if k not in excluded})

    def test_return_speed_opposes_displacement_and_is_bounded(self):
        for displacement in (-.2,-.04,.04,.2):
            c=PositionHoldController();c(frame(.005,{0:100.,1:-200.}),{0:0.,1:0.},PLAN)
            a=frame(.01,{0:100.+displacement/.04,1:-200.+displacement/.04})
            c(a,{0:0.,1:0.},PLAN)
            target=a['position_hold']['target_velocity_m_s']
            self.assertLess(target*displacement,0.);self.assertLessEqual(abs(target),.03)
            self.assertAlmostEqual(a['position_hold']['relative_error_proxy_m'],displacement)
            self.assertEqual(a['velocity_hold']['target_velocity_m_s'],target)
            self.assertLessEqual(abs(a['speed_pitch_reference_deg']),1.)
            for allocation in c.allocations.values():
                self.assertLessEqual(abs(allocation.predicted_net_nm),.12+1e-12)
            c.reset();a=frame(.015,{0:3.,1:9.});c(a,{0:0.,1:0.},PLAN)
            self.assertEqual(a['position_velocity_target_m_s'],0.)

    def test_zero_error_matches_previous_and_turning_does_not_shift_position(self):
        c=PositionHoldController();p=RelativeHeadingController()
        for i in range(1,100):
            a=frame(i*.005,{0:i*.001,1:-i*.001});b=copy.deepcopy(a)
            self.assertEqual(c(a,{0:.1,1:-.1},PLAN),p(b,{0:.1,1:-.1},BEFORE))
            self.assertEqual(a['position_hold']['relative_error_proxy_m'],0.)

    def test_missing_encoders_changed_config_and_bad_target_reject(self):
        c=PositionHoldController();a=frame(.005,{0:0.,1:0.});a.pop('wheel_position_forward_rad')
        with self.assertRaisesRegex(Fault,'requires_both_encoders'):c(a,{0:0.,1:0.},PLAN)
        c=PositionHoldController();c(frame(.005,{0:0.,1:0.}),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            c(frame(.01,{0:0.,1:0.}),{0:0.,1:0.},dict(PLAN,position_speed_kp_per_s=.6))
        a=frame(.005,{0:0.,1:0.});a['position_velocity_target_m_s']=.031
        with self.assertRaisesRegex(Fault,'target_outside_plan'):
            VelocityHoldController()(a,{0:0.,1:0.},PLAN)

    def test_runner_final_stop_and_no_rearm_after_cue_fault(self):
        for fail in (False,True):
            b=Bus(timeout=True);r={};cue=Indicator(b,fail)
            def tick():cue.check();cue.ticks+=1
            cue.tick=tick
            run({m:b.exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),r,True,
                now=b.now,sleep=b.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=PositionHoldController(),travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(r['status'],'FAIL' if fail else 'PASS');self.assertTrue(r['final_disabled_verified'])
            self.assertTrue(cue.off);self.assertEqual(r['balanced_operation'],'NOT_TESTED')
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
