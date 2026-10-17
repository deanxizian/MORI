import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from net_torque_adapter import NetTorquePitchController
from test_ardupilot_balance import pose
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_wheel_check import Bus
from two_deck_cued_balance import PLAN as PREVIOUS
from two_deck_zero_speed import PLAN,ZeroSpeedNetController,main


class ZeroSpeedNetTests(unittest.TestCase):
    def test_inert_default_and_only_reference_layer_changes(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        changes={'name','control_phase','active_message'}
        self.assertEqual({k:v for k,v in PREVIOUS.items() if k not in changes},
                         {k:PLAN[k] for k in PREVIOUS if k not in changes})

    def test_zero_speed_matches_previous_inner_controller(self):
        previous=NetTorquePitchController();new=ZeroSpeedNetController()
        for i in range(1,100):
            a=pose(i*.005,pitch=.5*math.sin(i*.03));a['dt']=.005
            b=copy.deepcopy(a)
            self.assertEqual(new(a,{0:0.,1:0.},PLAN),previous(b,{0:0.,1:0.},PREVIOUS))
            self.assertEqual(a['ardupilot_balance']['desired_pitch_forward_deg'],0.)

    def test_reference_sign_cap_slew_and_reset_match_existing_layer(self):
        for direction in (-1,1):
            c=ZeroSpeedNetController();last=0.
            for i in range(1,401):
                a=pose(i*.005);a['dt']=.005
                c(a,{0:direction*2.,1:direction*2.},PLAN)
                target=a['ardupilot_balance']['desired_pitch_forward_deg']
                self.assertLessEqual(abs(target),1.)
                self.assertLessEqual(abs(target-last),.010000001)
                self.assertLessEqual(abs(c.allocations[0].predicted_net_nm),.12+1e-12)
                last=target
            self.assertAlmostEqual(last,-direction,places=6)
            c.reset();a=pose(3.)
            c(a,{0:0.,1:0.},PLAN)
            self.assertEqual(a['ardupilot_balance']['desired_pitch_forward_deg'],0.)

    def test_dynamic_reference_is_bounded_separately_from_nominal_trim(self):
        for offset in (1.01,float('nan')):
            a=pose(.005);a['speed_pitch_reference_deg']=offset
            with self.assertRaises(Fault):NetTorquePitchController()(a,{0:0.,1:0.},PLAN)
        c=NetTorquePitchController()
        for i,offset in enumerate((-.8,0.,.8),1):
            a=pose(i*.005);a['speed_pitch_reference_deg']=offset
            c(a,{0:0.,1:0.},PLAN)
            self.assertAlmostEqual(a['ardupilot_balance']['desired_pitch_forward_deg'],offset)
        a=pose(.005);a['speed_pitch_reference_deg']=.8
        NetTorquePitchController()(a,{0:0.,1:0.},PREVIOUS)
        self.assertEqual(a['ardupilot_balance']['desired_pitch_forward_deg'],0.)

    def test_runner_final_stop_and_link_failure_preserve_cue_lifecycle(self):
        for fail in (False,True):
            b=Bus(timeout=True);r={};cue=Indicator(b,fail)
            # The test cue asserts the old phase; adapt only its inspection.
            def tick():cue.check();cue.ticks+=1
            cue.tick=tick
            run({m:b.exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),r,True,
                now=b.now,sleep=b.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=ZeroSpeedNetController(),travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(r['status'],'FAIL' if fail else 'PASS')
            self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
