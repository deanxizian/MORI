import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import unittest
from unittest.mock import patch

from test_two_deck_heading import frame
from two_deck_velocity_diagnostics import PLAN as BASE,VelocityDiagnosticsController
from two_deck_slow_wobble import PLAN,main


class SlowWobbleTests(unittest.TestCase):
    def test_default_and_incomplete_start_have_no_io_and_guards_do_not_change(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')), \
             patch('air_trial.run',side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):main(['--run-two-deck-slow-wobble','--operator-ready'])
        changed={k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)}
        self.assertEqual(changed,{'name','ap_ki','control_phase','active_message'})

    def test_integral_response_reduces_in_both_directions_without_changing_pd(self):
        for sign in (-1,1):
            old=VelocityDiagnosticsController();new=VelocityDiagnosticsController()
            for i in range(1,401):
                t=i*.005;a=frame(t,{0:0.,1:0.})
                a.update(pitch_deg=sign*.25,pitch_error_deg=sign*.25,
                         wheel_feedback_received_monotonic={0:t-.003,1:t-.002})
                b=copy.deepcopy(a);old(a,{0:0.,1:0.},BASE);new(b,{0:0.,1:0.},PLAN)
                pa,pb=a['ardupilot_balance'],b['ardupilot_balance']
                self.assertAlmostEqual(pb['i_nm'],pa['i_nm']/4.,places=12)
                for k in ('p_nm','d_nm','desired_pitch_forward_deg'):
                    self.assertEqual(pa[k],pb[k])
                self.assertTrue(all(abs(v)<=.12 for v in pb['predicted_net_forward_nm'].values()))
            new.reset();a=frame(3.,{0:0.,1:0.})
            a['wheel_feedback_received_monotonic']={0:2.997,1:2.998}
            new(a,{0:0.,1:0.},PLAN)
            self.assertEqual(a['ardupilot_balance']['i_nm'],0.)


if __name__=='__main__':unittest.main()
