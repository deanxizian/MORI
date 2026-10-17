import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import math
import unittest
from unittest.mock import patch

from test_two_deck_heading import frame
from two_deck_velocity_diagnostics import PLAN as BASE,VelocityDiagnosticsController
from two_deck_pitch_damping import PLAN,main


class PitchDampingTests(unittest.TestCase):
    def test_no_io_without_complete_unlock_and_no_change_to_guard_profile(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')), \
             patch('air_trial.run',side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):main(['--run-two-deck-pitch-damping','--operator-ready'])
        changed={k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)}
        self.assertEqual(changed,{'name','ap_kd','control_phase','active_message'})
        self.assertEqual(PLAN['ap_ki']*PLAN['output_scale_nm'],.6)

    def test_reversing_pitch_keeps_pd_components_distinct_and_resets_derivative(self):
        old=VelocityDiagnosticsController();new=VelocityDiagnosticsController()
        for i in range(1,801):
            t=i*.005;pitch=.2*math.sin(3*t)
            a=frame(t,{0:0.,1:0.});a.update(pitch_deg=pitch,pitch_error_deg=pitch,
                wheel_feedback_received_monotonic={0:t-.003,1:t-.002})
            b=copy.deepcopy(a);old(a,{0:0.,1:0.},BASE);new(b,{0:0.,1:0.},PLAN)
            pa,pb=a['ardupilot_balance'],b['ardupilot_balance']
            for k in ('p_nm','i_nm','desired_pitch_forward_deg'):
                self.assertEqual(pa[k],pb[k])
            self.assertAlmostEqual(pb['d_nm'],1.5*pa['d_nm'],places=12)
            self.assertTrue(all(abs(v)<=.12 for v in pb['predicted_net_forward_nm'].values()))
        new.reset();a=frame(5.,{0:0.,1:0.})
        a.update(pitch_deg=-.5,pitch_error_deg=-.5,
            wheel_feedback_received_monotonic={0:4.997,1:4.998})
        new(a,{0:0.,1:0.},PLAN)
        self.assertEqual(a['ardupilot_balance']['d_nm'],0.)
        self.assertTrue(a['ardupilot_balance']['filter_reset'])


if __name__=='__main__':unittest.main()
