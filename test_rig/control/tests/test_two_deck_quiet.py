import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from air_trial import run
from ground_hold_trial import HoldTravel
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_wheel_check import Bus
from two_deck_heading_hold import RelativeHeadingController
from two_deck_quiet_balance import PLAN,main


class QuietProfileTests(unittest.TestCase):
    def test_default_inert(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_new_gain_profile_runner_fault_stops_and_no_balance_claim(self):
        for fail in (False,True):
            b=Bus(timeout=True);r={};cue=Indicator(b,fail)
            def tick():cue.check();cue.ticks+=1
            cue.tick=tick
            run({m:b.exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),r,True,
                now=b.now,sleep=b.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=RelativeHeadingController(),travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(r['status'],'FAIL' if fail else 'PASS')
            self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
            self.assertEqual(r['balanced_operation'],'NOT_TESTED')
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
