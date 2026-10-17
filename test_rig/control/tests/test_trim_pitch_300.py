import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch
from test_two_deck_heading import frame
from two_deck_trim_pitch_gain_275 import PLAN as BASE
from two_deck_trim_pitch_gain_300 import PLAN,main
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


class Pitch300Tests(unittest.TestCase):
    def test_inert_default_and_only_p_changes(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertEqual({k for k in set(PLAN)|set(BASE) if PLAN.get(k)!=BASE.get(k)},
                         {'name','control_phase','active_message','ap_kp'})
        self.assertEqual(PLAN['duration_s'],30.)
        self.assertEqual(PLAN['ap_kp']*PLAN['output_scale_nm'],3.)

    def test_dynamic_p_scaling_keeps_id_and_integer_command_budgets(self):
        old=VelocityDiagnosticsController();new=VelocityDiagnosticsController()
        for i in range(1,801):
            t=i*.005;a=frame(t,{0:0.,1:0.})
            a.update(pitch_deg=.2*math.sin(3*t),pitch_error_deg=.2*math.sin(3*t),
                     wheel_feedback_received_monotonic={0:t-.003,1:t-.002})
            b=copy.deepcopy(a);old(a,{0:0.,1:0.},BASE);out=new(b,{0:0.,1:0.},PLAN)
            pa,pb=a['ardupilot_balance'],b['ardupilot_balance']
            self.assertAlmostEqual(pb['p_nm'],pa['p_nm']*3/2.75,places=12)
            for k in ('i_nm','d_nm','desired_pitch_forward_deg'):self.assertEqual(pa[k],pb[k])
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(len(new.allocated_torque_packet(mid,sign,out[mid],PLAN)),20)
                self.assertLessEqual(abs(new.allocations[mid].feedforward_nm),.12)
                self.assertLessEqual(abs(new.allocations[mid].predicted_net_nm),.12)


if __name__=='__main__':unittest.main()
