import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch
from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from offline_two_deck_review_20261016.motor_stage import scaled_throttle_pct
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_two_deck_heading import frame
from test_wheel_check import Bus
from two_deck_heading_hold import PLAN as BASE
from two_deck_motor_shape import PLAN,MotorShapeController,main


class MotorShapeTests(unittest.TestCase):
    def test_default_inert_and_original_controller_gains_retained(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        excluded={'name','duration_s','wheel_speed_limit_rad_s','control_phase','active_message'}
        self.assertEqual({k:v for k,v in BASE.items() if k not in excluded},
                         {k:PLAN[k] for k in BASE if k not in excluded})
        self.assertNotIn('allow_position_velocity_target',PLAN)

    def test_exact_percent_boundary_zero_sign_and_no_unit_factor_error(self):
        c=MotorShapeController()
        for tau in (-.20,-.12,-.03,-.001,0.,.001,.03,.12,.20):
            a={};shaped,limited=c.shape_common_net_request(tau,a,PLAN)
            expected=scaled_throttle_pct(100*max(-1.,min(1.,tau/.12)),15.,0.)*.0012
            self.assertAlmostEqual(shaped,expected)
            self.assertLessEqual(abs(shaped),.12+1e-12)
            self.assertEqual(limited,abs(tau)>.12)
            if tau==0:self.assertEqual(shaped,0.)
            else:self.assertGreater(shaped*tau,0.)

    def test_shaped_requests_and_differential_mix_keep_integer_budgets(self):
        for pitch in (-19.,-1.,0.,1.,19.):
            for speed in (-5.9,0.,5.9):
                c=MotorShapeController();a=frame(.005,{0:0.,1:0.});a['pitch_deg']=a['pitch_error_deg']=pitch
                commands=c(a,{0:speed,1:-speed},PLAN)
                for m in (0,1):
                    self.assertEqual(len(c.allocated_torque_packet(m,1 if m==0 else -1,commands[m],PLAN)),20)
                    self.assertLessEqual(abs(c.allocations[m].predicted_net_nm),.12+1e-12)
                    self.assertLessEqual(abs(c.allocations[m].feedforward_nm),.12+1e-12)
                self.assertLessEqual(abs(a['wheel_sync']['correction_nm']),.015)
        c=MotorShapeController();a=frame(.005,{0:0.,1:0.});a['pitch_deg']=a['pitch_error_deg']=19.
        c(a,{0:0.,1:0.},PLAN);self.assertTrue(c.previous_limited)

    def test_changed_or_unreviewed_curve_rejects(self):
        c=MotorShapeController();c.shape_common_net_request(0.,{},PLAN)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            c.shape_common_net_request(0.,{},dict(PLAN,ap_motor_minimum_pct=14.))
        for change in ({'ap_motor_minimum_pct':16.},{'ap_motor_expo':-.5}):
            with self.assertRaisesRegex(Fault,'configuration_outside_plan'):
                MotorShapeController().shape_common_net_request(0.,{},dict(PLAN,**change))

    def test_runner_final_stop_after_complete_window_or_display_fault(self):
        for fail in (False,True):
            b=Bus(timeout=True);r={};cue=Indicator(b,fail)
            def tick():cue.check();cue.ticks+=1
            cue.tick=tick
            run({m:b.exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),r,True,
                now=b.now,sleep=b.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=MotorShapeController(),travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(r['status'],'FAIL' if fail else 'PASS');self.assertTrue(r['final_disabled_verified'])
            self.assertTrue(cue.off);self.assertEqual(r['balanced_operation'],'NOT_TESTED')
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
