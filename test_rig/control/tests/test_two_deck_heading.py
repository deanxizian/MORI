import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from test_ardupilot_balance import pose
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_wheel_check import Bus
from two_deck_heading_hold import PLAN,RelativeHeadingController,main
from two_deck_synced_balance import PLAN as BEFORE


def frame(t,positions):
    a=pose(t);a['dt']=.005;a['wheel_position_forward_rad']=positions
    return a


class RelativeHeadingTests(unittest.TestCase):
    def test_inert_default_and_existing_budgets_parameters_retained(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        excluded={'name','active_message','control_phase','include_wheel_position_feedback'}
        self.assertEqual({k:v for k,v in BEFORE.items() if k not in excluded},
                         {k:PLAN[k] for k in BEFORE if k not in excluded})

    def test_encoder_difference_corrects_left_right_and_common_motion_is_ignored(self):
        for delta in (-.75,.75):
            c=RelativeHeadingController();c(frame(.005,{0:100.,1:-200.}),{0:0.,1:0.},PLAN)
            a=frame(.01,{0:105.+delta,1:-195.})
            c(a,{0:0.,1:0.},PLAN)
            info=a['wheel_sync'];requests=a['ardupilot_balance']['requested_net_per_wheel_nm']
            self.assertAlmostEqual(info['relative_position_error_rad'],delta)
            self.assertLess(info['correction_nm']*delta,0)
            self.assertLessEqual(abs(info['correction_nm']),.015)
            self.assertAlmostEqual(sum(requests.values())/2,a['ardupilot_balance']['requested_net_nm'])
            c.reset();a=frame(.015,{0:105.+delta,1:-195.})
            c(a,{0:0.,1:0.},PLAN);self.assertEqual(a['wheel_sync']['correction_nm'],0.)

    def test_missing_position_or_changed_gain_rejects(self):
        c=RelativeHeadingController()
        with self.assertRaisesRegex(Fault,'requires_both_positions'):c(pose(.005),{0:0.,1:0.},PLAN)
        # A rejected controller is never automatically reused/re-armed.
        c=RelativeHeadingController()
        c(frame(.005,{0:0.,1:0.}),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'heading_gain_changed'):
            c(frame(.01,{0:0.,1:0.}),{0:0.,1:0.},dict(PLAN,heading_kp_nm_per_rad=.021))

    def test_runner_positions_final_stop_and_link_failure(self):
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
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
