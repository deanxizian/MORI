import io
import struct
from air_trial import velocity_packet
from protocol import RATIO
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from attitude import Fault
from self_righting_velocity_preparation import PLAN,VelocityPreparation,main
from self_righting_synced_preparation import PLAN as REFERENCE,main as used_main


class VelocityPreparationTests(unittest.TestCase):
    def frame(self,t,pos=None):
        return dict(t=t,dt=.01,pitch_deg=90.,pitch_rate_dps=0.,pitch_error_deg=90.,roll_deg=0.,
            wheel_position_forward_rad=pos or {0:0.,1:0.},
            wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def test_only_preparation_interface_changes(self):
        keys={'name','active_message','motion_hold_reason','preparation_velocity_kd_nm_per_rad_s',
              'preparation_velocity_target_limit_rad_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in REFERENCE.items() if k not in keys})
        self.assertFalse(PLAN.get('native_velocity_control',False))

    def test_preparation_uses_zero_ff_and_bounded_native_targets(self):
        c=VelocityPreparation();c(self.frame(0.),{0:0.,1:0.},PLAN)
        ff=c(self.frame(.01,{0:-.098,1:-.09}),{0:-9.8,1:-9.},PLAN)
        p=c.motor_plan(PLAN);state=c.preparation_targets
        self.assertEqual(c.phase,'PRE_ROLL');self.assertEqual(ff,{0:0.,1:0.})
        self.assertTrue(p['native_velocity_control']);self.assertEqual(p['feedforward_torque_limit_nm'],0.)
        self.assertTrue(all(abs(v)<=10. for v in state.values()))
        self.assertEqual(p['velocity_targets_forward_rad_s'],state)
        self.assertLessEqual(abs(c.previous_net_common),PLAN['predicted_net_torque_limit_nm'])

    def test_native_packet_has_no_position_stiffness_or_feedforward(self):
        c=VelocityPreparation();c(self.frame(0.),{0:0.,1:0.},PLAN)
        c(self.frame(.01,{0:-.098,1:-.09}),{0:-9.8,1:-9.},PLAN)
        p=c.motor_plan(PLAN)
        packet=velocity_packet(0,c.preparation_targets[0],p)
        torque,velocity,position,kp,kd=struct.unpack('<hhihh',packet[4:16])
        self.assertEqual((torque,position,kp),(0,0,0))
        self.assertLessEqual(abs(velocity*6.283185307179586/(2.56*RATIO)),10.)
        self.assertGreater(kd,0)
        self.assertEqual(p['wheel_speed_limit_rad_s'],13.)

    def test_handoff_uses_native_net_and_restores_torque_path(self):
        c=VelocityPreparation();c(self.frame(0.),{0:0.,1:0.},PLAN)
        c(self.frame(.01,{0:-.098,1:-.09}),{0:-9.8,1:-9.},PLAN)
        prior=c.previous_net_common
        c(self.frame(.02,{0:-.195,1:-.187}),{0:-9.7,1:-9.7},PLAN)
        self.assertEqual(c.phase,'RISING');self.assertAlmostEqual(c.rise_initial_common,prior)
        p=c.motor_plan(PLAN)
        self.assertFalse(p.get('native_velocity_control',False))
        self.assertNotIn('velocity_targets_forward_rad_s',p)
        self.assertEqual(p['native_wheel_damping_nm_per_rad_s'],.001)

    def test_preparation_speed_fault_still_latches(self):
        c=VelocityPreparation();c(self.frame(0.),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'pre_roll_speed_stop'):
            c(self.frame(.01,{0:-.131,1:-.131}),{0:-13.1,1:-13.1},PLAN)
        with self.assertRaisesRegex(Fault,'fault_latched'):
            c(self.frame(.02),{0:0.,1:0.},PLAN)

    def test_invalid_target_and_unattained_deadline_reject(self):
        with self.assertRaisesRegex(Fault,'invalid_preparation_velocity_plan'):
            VelocityPreparation().validate_arm(self.frame(0.),{0:0.,1:0.},dict(PLAN,preparation_velocity_target_limit_rad_s=13.))
        c=VelocityPreparation()
        with self.assertRaisesRegex(Fault,'preparation_velocity_not_reached_before_timeout'):
            for i in range(42):c(self.frame(i*.01),{0:0.,1:0.},PLAN)

    def test_default_inert_and_used_entry_locked_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):
                used_main(['--run-synced-preparation','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
