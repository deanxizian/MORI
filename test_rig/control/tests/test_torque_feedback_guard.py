import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from air_trial import health,run
from attitude import Fault
from ground_hold_trial import HoldTravel
from ground_trial import ground_command
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_wheel_check import Bus
from torque_feedback_guard import TorqueFeedbackGuard
from two_deck_recovery_observe import PLAN,RelativeHeadingController,main
from two_deck_speed_response import PLAN as BEFORE


class TorqueFeedbackGuardTests(unittest.TestCase):
    def test_default_is_inert_and_legacy_health_still_rejects_0122(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        b=Bus();row=b.exchange(0)(bytes([0,0,0])+bytes(17),'disabled')
        with self.assertRaisesRegex(Fault,'estimated_torque_stop'):
            health(dict(row,torque_estimate_nm=.122),0,plan=BEFORE)

    def test_small_estimate_overshoot_does_not_change_command_budget(self):
        g=TorqueFeedbackGuard(PLAN)
        for i in range(40):
            for m in (0,1):g.observe(m,(-1 if m else 1)*.122,i*.005)
        self.assertEqual(g.audit['per_id'][0]['above_original_frames'],40)
        hp=g.motor_health_plan(PLAN)
        self.assertEqual(hp['estimated_torque_limit_nm'],.15)
        for k in ('feedforward_torque_limit_nm','predicted_net_torque_limit_nm'):
            self.assertEqual(hp[k],.12)

    def test_short_spikes_clear_and_two_wheels_cannot_reset_each_other(self):
        g=TorqueFeedbackGuard(PLAN)
        for i in range(10):
            g.observe(0,.14 if i<8 else .12,i*.005)
            g.observe(1,.12,i*.005)
        for i in range(10,21):
            g.observe(1,.12,i*.005)
            if i==20:
                with self.assertRaisesRegex(Fault,'sustained_stop'):g.observe(0,-.14,i*.005)
            else:g.observe(0,-.14,i*.005)
        with self.assertRaisesRegex(Fault,'latched'):g.observe(0,0.,.11)

    def test_hard_limit_is_immediate_and_bad_feedback_is_never_filtered(self):
        with self.assertRaisesRegex(Fault,'estimated_torque_stop'):
            TorqueFeedbackGuard(PLAN).observe(1,.151,1.)
        for value in (float('nan'),float('inf')):
            with self.assertRaises(Fault):TorqueFeedbackGuard(PLAN).observe(0,value,1.)
        for next_t in (1.,.999,1.026):
            g=TorqueFeedbackGuard(PLAN);g.observe(0,.14,1.)
            with self.assertRaisesRegex(Fault,'sample_gap'):g.observe(0,.14,next_t)

    def test_configuration_must_be_bounded_and_frozen(self):
        for change in ({'torque_feedback_soft_nm':.131},{'torque_feedback_hard_nm':.151},
                       {'torque_feedback_dwell_s':.051},{'feedforward_torque_limit_nm':.121}):
            with self.assertRaisesRegex(Fault,'outside_plan'):TorqueFeedbackGuard(dict(PLAN,**change))
        g=TorqueFeedbackGuard(PLAN)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            g.motor_health_plan(dict(PLAN,torque_feedback_soft_nm=.129))

    def test_pitch_recovery_window_is30deg_but_roll_and_commands_stay_bounded(self):
        for pitch in (-29.99,29.99):
            a=dict(pitch_deg=pitch,pitch_rate_dps=0.,roll_deg=0.)
            commands=ground_command(a,{0:0.,1:0.},PLAN)
            self.assertTrue(all(abs(t)<=.12 for t in commands.values()))
            with self.assertRaisesRegex(Fault,'body_tilt_stop'):
                ground_command(dict(a,pitch_deg=30.01),{0:0.,1:0.},PLAN)
            with self.assertRaisesRegex(Fault,'body_tilt_stop'):
                ground_command(dict(a,roll_deg=8.01),{0:0.,1:0.},PLAN)

    def run_case(self,changes=None,cue_fail=False):
        b=Bus(timeout=True);r={};cue=Indicator(b,cue_fail)
        def tick():cue.check();cue.ticks+=1
        cue.tick=tick
        def exchange(mid):
            original=b.exchange(mid)
            def call(packet,phase):
                row=original(packet,phase)
                if phase==PLAN['control_phase']:
                    row.update(changes or {'torque_estimate_nm':.122})
                return row
            return call
        run({m:exchange(m) for m in (0,1)},HandIMU(b),copy.deepcopy(CAL),r,True,
            now=b.now,sleep=b.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.2,post_stop_observation_s=0.),
            controller=RelativeHeadingController(),travel_factory=HoldTravel,indicator=cue)
        self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
        stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
        self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))
        self.assertEqual(r['balanced_operation'],'NOT_TESTED')
        return r

    def test_runner_accepts_margin_but_stops_on_persistent_and_hard_estimate(self):
        self.assertEqual(self.run_case()['status'],'PASS')
        r=self.run_case({'torque_estimate_nm':.14})
        self.assertEqual(r['reason'],'estimated_torque_sustained_stop')
        self.assertGreaterEqual(r['elapsed_s'],.05)
        self.assertLess(r['elapsed_s'],.08)
        self.assertEqual(self.run_case({'torque_estimate_nm':.151})['reason'],'estimated_torque_stop')

    def test_other_guards_and_display_fault_still_stop_immediately(self):
        for changes,reason in (({'temperature_c':70},'servo_temperature_stop'),
                               ({'speed_rad_s':6.01},'wheel_speed_stop'),
                               ({'warning_raw':1},'servo_mode_error_or_warning')):
            self.assertEqual(self.run_case(changes)['reason'],reason)
        self.assertEqual(self.run_case(cue_fail=True)['reason'],'cam_ack_lost')


if __name__=='__main__':unittest.main()
