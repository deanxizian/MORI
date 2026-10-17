import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import math
import unittest
from unittest.mock import patch

from test_two_deck_heading import frame
from two_deck_drive_headroom import PLAN as BASE
from two_deck_heading_hold import RelativeHeadingController
from two_deck_velocity_diagnostics import PLAN,VelocityDiagnosticsController,main


class VelocityDiagnosticsTests(unittest.TestCase):
    def test_candidate_is_inert_and_requires_complete_explicit_start(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')), \
             patch('air_trial.run',side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):main(['--run-two-deck-velocity-diagnostics','--operator-ready'])
        self.assertNotIn('motion_hold_reason',PLAN)

    def test_shadow_diagnostics_leave_both_command_packets_identical(self):
        new=VelocityDiagnosticsController();old=RelativeHeadingController()
        for i in range(1,401):
            t=i*.005;a=frame(t,{0:.1*math.sin(t),1:.1*math.sin(t+.1)})
            a.update(pitch_deg=math.sin(t*2),pitch_rate_dps=2*math.cos(t*2),
                     wheel_feedback_received_monotonic={0:t-.003,1:t-.002})
            speeds={0:math.sin(t*3),1:math.sin(t*3+.1)};b=copy.deepcopy(a)
            nc=new(a,speeds,PLAN);oc=old(b,speeds,BASE)
            self.assertEqual(nc,oc)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(new.allocated_torque_packet(mid,sign,nc[mid],PLAN),
                                 old.allocated_torque_packet(mid,sign,oc[mid],BASE))
            if i>1:self.assertTrue(a['velocity_frame_diagnostics']['ready'])

    def test_invalid_shadow_time_is_explicit_without_changing_baseline_output(self):
        new=VelocityDiagnosticsController();old=RelativeHeadingController()
        a=frame(.005,{0:0.,1:0.});a['wheel_feedback_received_monotonic']={0:.1,1:.1}
        b=copy.deepcopy(a)
        self.assertEqual(new(a,{0:0.,1:0.},PLAN),old(b,{0:0.,1:0.},BASE))
        self.assertEqual(a['velocity_frame_diagnostics']['status'],'INVALID')
        self.assertIsNone(a['velocity_frame_diagnostics']['corrected_proxy_m_s'])


if __name__=='__main__':unittest.main()
