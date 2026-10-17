import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from attitude import Fault
from test_ardupilot_balance import pose
from two_deck_synced_balance import PLAN,SynchronizedZeroSpeedController,main
from two_deck_zero_speed import PLAN as PREVIOUS,ZeroSpeedNetController


class SyncedTests(unittest.TestCase):
    def test_default_inert_and_existing_limits_gains_unchanged(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        excluded={'name','control_phase','active_message'}
        self.assertEqual({k:v for k,v in PREVIOUS.items() if k not in excluded},
                         {k:PLAN[k] for k in PREVIOUS if k not in excluded})

    def test_equal_wheels_match_previous_controller(self):
        before=ZeroSpeedNetController();after=SynchronizedZeroSpeedController()
        for i in range(1,101):
            a=pose(i*.005,pitch=.4);a['dt']=.005;b=copy.deepcopy(a)
            self.assertEqual(after(a,{0:-1.,1:-1.},PLAN),before(b,{0:-1.,1:-1.},PREVIOUS))
            self.assertEqual(a['wheel_sync']['correction_nm'],0.)

    def test_correction_opposes_rate_difference_and_preserves_common(self):
        for speeds in ({0:-1.8,1:0.},{0:0.,1:-1.8},{0:2.,1:0.},{0:-3.,1:3.}):
            c=SynchronizedZeroSpeedController()
            for i in range(1,30):
                a=pose(i*.005,pitch=-.5);a['dt']=.005;c(a,speeds,PLAN)
                info=a['ardupilot_balance'];requests=info['requested_net_per_wheel_nm']
                self.assertAlmostEqual(sum(requests.values())/2,info['requested_net_nm'])
                self.assertLessEqual((requests[0]-requests[1])*(speeds[0]-speeds[1]),1e-12)
                self.assertLessEqual(abs(a['wheel_sync']['correction_nm']),.015)
                for allocation in c.allocations.values():
                    self.assertLessEqual(abs(allocation.predicted_net_nm),.12+1e-12)
                    self.assertLessEqual(abs(allocation.feedforward_nm),.12+1e-12)

    def test_pitch_priority_configuration_rejection_and_fresh_reset(self):
        c=SynchronizedZeroSpeedController()
        for i in range(1,30):
            a=pose(i*.005,pitch=10.);a['dt']=.005;c(a,{0:-2.,1:2.},PLAN)
            self.assertEqual(a['wheel_sync']['available_margin_nm'],0.)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            c(pose(.15),{0:0.,1:0.},dict(PLAN,sync_kp_nm_per_rad_s=.011))
        c.reset();self.assertEqual(c.filtered_difference,0.);self.assertFalse(c.allocations)
        with self.assertRaisesRegex(Fault,'configuration_outside_plan'):
            c(pose(.005),{0:0.,1:0.},dict(PLAN,sync_limit_nm=.02))


if __name__=='__main__':unittest.main()
