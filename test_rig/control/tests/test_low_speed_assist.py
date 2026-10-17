import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import math
import unittest
from unittest.mock import patch

from attitude import Fault
from test_two_deck_heading import frame
from two_deck_velocity_diagnostics import PLAN as BASE,VelocityDiagnosticsController
from two_deck_low_speed_assist import PLAN,LowSpeedAssistController,smooth_assist,main


class LowSpeedAssistTests(unittest.TestCase):
    def test_inert_entry_and_existing_control_guards_unchanged(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')), \
             patch('air_trial.run',side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):main(['--run-two-deck-low-speed-assist','--operator-ready'])
        self.assertEqual({k for k in BASE if BASE[k]!=PLAN[k]},
                         {'name','control_phase','active_message'})

    def test_zero_continuity_fade_direction_and_total_headroom(self):
        for maximum in (0.,.001,.005,.009,.012):
            for speed in (-6.,-.5,-.05,-.001,0.,.001,.05,.5,6.):
                self.assertEqual(smooth_assist(0.,speed,maximum,.02,.5,.05,.12),0.)
                for req in (-.2,-.12,-.1199,-.03,-1e-9,1e-9,.03,.1199,.12,.2):
                    assist=smooth_assist(req,speed,maximum,.02,.5,.05,.12)
                    self.assertGreaterEqual(assist*req,0.)
                    self.assertLessEqual(abs(assist),maximum+1e-12)
                    if abs(req)<=.12:self.assertLessEqual(abs(req+assist),.12+1e-12)
                    else:self.assertEqual(assist,0.)
                    if abs(speed)>=.5 or speed*math.copysign(1,req)<=-.05:
                        self.assertEqual(assist,0.)
                    if abs(req)<1e-8:self.assertLessEqual(abs(assist),.6*abs(req)+1e-15)

    def test_same_pid_outputs_exact_packets_and_no_extra_output_at_speed(self):
        for speed in (-5.9,-.5,0.,.5,5.9):
            for pitch in (-10.,-.5,0.,.5,10.):
                old=VelocityDiagnosticsController();new=LowSpeedAssistController()
                a=frame(.005,{0:0.,1:0.});a.update(pitch_deg=pitch,pitch_error_deg=pitch,
                    wheel_feedback_received_monotonic={0:.002,1:.003})
                b=copy.deepcopy(a);old_cmd=old(a,{0:speed,1:speed},BASE)
                cmd=new(b,{0:speed,1:speed},PLAN)
                for key in ('p_nm','i_nm','d_nm','desired_pitch_forward_deg'):
                    self.assertEqual(a['ardupilot_balance'][key],b['ardupilot_balance'][key])
                if abs(speed)>=.5:self.assertEqual(old_cmd,cmd)
                for mid,sign in ((0,1),(1,-1)):
                    new.allocated_torque_packet(mid,sign,cmd[mid],PLAN)
                    self.assertLessEqual(abs(cmd[mid]),.12+1e-12)
                    self.assertLessEqual(abs(b['ardupilot_balance']['predicted_net_forward_nm'][mid]),.12+1e-12)

    def test_invalid_or_changed_configuration_faults_and_reset_is_empty(self):
        c=LowSpeedAssistController();a=frame(.005,{0:0.,1:0.})
        c(a,{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'changed_during_run'):
            c(frame(.01,{0:0.,1:0.}),{0:0.,1:0.},dict(PLAN,low_speed_assist_request_scale_nm=.03))
        c.reset();self.assertIsNone(c.assist_configuration)
        for params in (dict(low_speed_assist_nm=((.013,.001),(.005,.012))),
                       dict(low_speed_assist_fade_rad_s=1.),
                       dict(low_speed_assist_request_scale_nm=float('nan'))):
            with self.assertRaises(Fault):
                LowSpeedAssistController()(frame(.005,{0:0.,1:0.}),{0:0.,1:0.},dict(PLAN,**params))


if __name__=='__main__':unittest.main()
