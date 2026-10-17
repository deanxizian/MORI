import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from self_righting_transfer_ramp import PLAN,main
from self_righting_morning_supply import PLAN as REFERENCE
from self_righting_supervised import SupervisedRecovery


class TransferRampTests(unittest.TestCase):
    def frame(self,t):
        return dict(t=t,dt=.01,pitch_deg=90.,pitch_rate_dps=0.,
                    pitch_error_deg=90.,roll_deg=0.,
                    wheel_position_forward_rad={0:0.,1:0.},
                    wheel_feedback_received_monotonic={0:t-.002,1:t-.001})

    def trace(self,plan):
        c=SupervisedRecovery();result=[]
        for i in range(58):
            a=self.frame(i*.01);commands=c(a,{0:0.,1:0.},plan)
            result.append((a['self_righting'],commands))
        return result

    def test_only_reversal_duration_changes(self):
        metadata={'name','active_message','motion_hold_reason','rise_ramp_s'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in metadata},
                         {k:v for k,v in REFERENCE.items() if k not in metadata})
        self.assertEqual(PLAN['rise_ramp_s'],.15)
        self.assertEqual(PLAN['recovery_rate_max_dps'],400.)

    def test_reversal_step_is_smaller_but_final_request_is_preserved(self):
        old=self.trace(REFERENCE);new=self.trace(PLAN)
        old_steps=[abs(old[i][0]['common_request_nm']-old[i-1][0]['common_request_nm']) for i in range(41,49)]
        new_steps=[abs(new[i][0]['common_request_nm']-new[i-1][0]['common_request_nm']) for i in range(41,49)]
        self.assertLess(max(new_steps),max(old_steps))
        self.assertAlmostEqual(new[-1][0]['common_request_nm'],old[-1][0]['common_request_nm'])

    def test_synthetic_reversal_requests_stay_inside_retained_force_budget(self):
        for state,commands in self.trace(PLAN):
            self.assertTrue(all(abs(v)<=PLAN['predicted_net_torque_limit_nm'] for v in commands.values()))
            self.assertEqual(state['applied_wheel_speed_limit_rad_s'],15.5)

    def test_default_has_no_file_or_motor_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)


if __name__=='__main__':unittest.main()
