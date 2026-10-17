import io
import math
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from attitude import Fault
from self_righting_supervised import PLAN,SupervisedRecovery,main
from self_righting_lift_trial import LIFT_PLAN
from self_righting_rate_profile import RATE_PROFILE_PLAN


class SupervisedTests(unittest.TestCase):
    def frame(self,t,pitch=90.,rate=0.,position=0.):
        return dict(t=t,dt=.01,pitch_deg=pitch,pitch_rate_dps=rate,roll_deg=0.,
            pitch_error_deg=pitch,wheel_position_forward_rad={0:position,1:position})

    def controller_in_rise(self):
        c=SupervisedRecovery()
        for i in range(42):c(self.frame(i*.01),{0:0.,1:0.},PLAN)
        self.assertEqual(c.phase,'RISING')
        return c

    def test_inert_default_and_retired_entries_still_held(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertTrue(LIFT_PLAN.get('motion_hold_reason'))
        self.assertTrue(RATE_PROFILE_PLAN.get('motion_hold_reason'))
        self.assertIn('trial33_overturn',PLAN['motion_hold_reason'])

    def test_capture_starts_before_stable_but_cannot_claim_success(self):
        c=self.controller_in_rise()
        c(self.frame(.42,16.,-80.,.05),{0:8.,1:8.},PLAN)
        self.assertEqual(c.phase,'CAPTURE')
        with self.assertRaisesRegex(Fault,'stable_window_not_met'):c.finish()

    def test_progress_reversal_enters_planned_exit_and_cannot_restart(self):
        c=self.controller_in_rise()
        c(self.frame(.42,70.,-100.,.01),{0:1.,1:1.},PLAN)
        for i in range(1,5):c(self.frame(.42+i*.01,73.,50.,.01+i*.01),{0:1.,1:1.},PLAN)
        self.assertEqual(c.phase,'ABORT_BRAKE')
        self.assertEqual(c.abort_reason,'lift_progress_reversed')
        self.assertFalse(c.fault)
        start=c.abort_previous;pos=c.abort_positions[0]
        for i in range(1,150):
            # A coherent recorded-input unit trace, not a plant simulation.
            v=max(0.,1.-i*.05);pos+=v*.01
            c(self.frame(start+i*.01,90.,0.,pos),{0:v,1:v},PLAN)
        self.assertEqual(c.phase,'ABORT_RELEASE')
        self.assertEqual(c.abort_targets,{0:0.,1:0.})
        self.assertEqual(c.motor_plan(PLAN)['native_wheel_damping_nm_per_rad_s'],0.)
        with self.assertRaisesRegex(Fault,'planned_abort'):c.finish()

    def test_hard_fault_is_not_converted_to_normal_exit(self):
        c=self.controller_in_rise()
        with self.assertRaisesRegex(Fault,'body_rotation_rate_stop'):
            c(self.frame(.42,70.,450.),{0:1.,1:1.},PLAN)
        self.assertEqual(c.phase,'FAULT');self.assertIsNone(c.abort_reason)
        with self.assertRaisesRegex(Fault,'fault_latched'):
            c(self.frame(.43),{0:0.,1:0.},PLAN)

    def test_fading_momentum_exits_before_rate_reverses(self):
        c=self.controller_in_rise()
        c(self.frame(.42,65.,-180.,.09),{0:9.,1:9.},PLAN)
        c(self.frame(.43,64.,-40.,.18),{0:9.,1:9.},PLAN)
        self.assertEqual(c.phase,'ABORT_BRAKE')
        self.assertEqual(c.abort_reason,'inward_momentum_fading_far_from_capture')
        self.assertFalse(c.fault)

    def test_hard_fault_during_normal_exit_remains_latched(self):
        c=self.controller_in_rise()
        a=self.frame(.42,70.,0.,.01)
        c.start_abort('test_healthy_exit',a,{0:1.,1:1.},PLAN)
        with self.assertRaisesRegex(Fault,'body_tilt_stop'):
            c(self.frame(.43,101.,0.,.02),{0:1.,1:1.},PLAN)
        self.assertEqual(c.phase,'FAULT')
        with self.assertRaisesRegex(Fault,'fault_latched'):
            c(self.frame(.44),{0:0.,1:0.},PLAN)

    def test_abort_plan_mutation_rejected(self):
        c=self.controller_in_rise();a=self.frame(.42)
        c.start_abort('test_healthy_exit',a,{0:0.,1:0.},PLAN)
        bad=dict(PLAN,abort_decel_rad_s2=20.)
        with self.assertRaisesRegex(Fault,'parameters_changed'):
            c(self.frame(.43),{0:0.,1:0.},bad)


if __name__=='__main__':unittest.main()
