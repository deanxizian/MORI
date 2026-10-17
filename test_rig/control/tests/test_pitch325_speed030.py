import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch
from test_two_deck_heading import frame
from two_deck_trim_pitch_gain_325 import PLAN as BASE
from two_deck_pitch325_speed030 import PLAN,main
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


class Pitch325Speed030Tests(unittest.TestCase):
    def test_default_inert_only_outer_gain_changes(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertEqual({k for k in set(PLAN)|set(BASE) if PLAN.get(k)!=BASE.get(k)},
                         {'name','control_phase','active_message','speed_kp_rad_per_m_s'})
        self.assertEqual(PLAN['duration_s'],30.)
        self.assertEqual(PLAN['ap_kp']*PLAN['output_scale_nm'],3.25)

    def test_speed_reference_brakes_both_directions_with_integer_budgets(self):
        old=VelocityDiagnosticsController();new=VelocityDiagnosticsController()
        for i in range(1,1601):
            t=i*.005
            speeds={0:1.2*math.sin(2*t),1:1.1*math.sin(2*t)}
            a=frame(t,speeds)
            a.update(pitch_deg=.3*math.sin(3*t),pitch_error_deg=.3*math.sin(3*t),
                     wheel_feedback_received_monotonic={0:t-.003,1:t-.002})
            b=copy.deepcopy(a)
            old(a,speeds,BASE);out=new(b,speeds,PLAN)
            v=b['velocity_hold'];prior=a['velocity_hold']
            self.assertEqual(v['filtered_velocity_proxy_m_s'],prior['filtered_velocity_proxy_m_s'])
            self.assertLessEqual(v['desired_pitch_reference_deg']*v['filtered_velocity_proxy_m_s'],1e-12)
            self.assertAlmostEqual(v['desired_pitch_reference_deg'],prior['desired_pitch_reference_deg']*1.2,places=12)
            self.assertLessEqual(abs(v['pitch_reference_deg']),PLAN['speed_pitch_reference_limit_deg'])
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(len(new.allocated_torque_packet(mid,sign,out[mid],PLAN)),20)
                self.assertLessEqual(abs(new.allocations[mid].feedforward_nm),.12)
                self.assertLessEqual(abs(new.allocations[mid].predicted_net_nm),.12)


if __name__=='__main__':unittest.main()
