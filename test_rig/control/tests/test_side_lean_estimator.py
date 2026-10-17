"""Known rotations and acceleration disturbances, not plant simulation."""
import math
import unittest

from attitude import Fault,PitchEstimator
from self_righting_trial import SELF_RIGHT_PLAN,SelfRightingController
from test_attitude_air import CAL


def frame(t,accel,gyro=(0.,0.,0.)):
    return dict(t_read_complete=t,accel_g=accel,gyro_dps=list(gyro))


class SideLeanTests(unittest.TestCase):
    def test_lateral_acceleration_step_does_not_masquerade_as_instant_tilt(self):
        legacy=PitchEstimator(CAL);fused=PitchEstimator(CAL,fuse_roll=True)
        initial=frame(.01,[1,0,0])
        legacy.update(initial);fused.update(initial)
        pulse=frame(.02,[.75,-.15,0])
        old=legacy.update(pulse);new=fused.update(pulse)
        self.assertGreater(old['roll_deg'],11)
        self.assertAlmostEqual(new['roll_deg'],0)
        self.assertAlmostEqual(old['pitch_deg'],new['pitch_deg'])
        self.assertAlmostEqual(new['roll_accel_deg'],old['roll_deg'])

    def test_real_lateral_rotation_trips_original_eight_degree_guard_at_both_lying_sides(self):
        for sign in (-1,1):
            estimator=PitchEstimator(CAL,fuse_roll=True);controller=SelfRightingController()
            for i in range(1,13):
                angle=math.radians(max(0,i-1))
                # A known rigid rotation about sensor Z, starting at +/-90
                # pitch; the measured gravity follows the inverse rotation.
                a=estimator.update(frame(i*.01,[sign*math.cos(angle),-math.sin(angle),0],
                    [0,0,0 if i==1 else sign*100]))
                a['wheel_position_forward_rad']={0:0.,1:0.}
                self.assertAlmostEqual(a['roll_deg'],max(0,i-1),places=5)
                if i-1<=8: controller(a,{0:0.,1:0.},SELF_RIGHT_PLAN)
                else:
                    with self.assertRaisesRegex(Fault,'body_tilt_stop'):
                        controller(a,{0:0.,1:0.},SELF_RIGHT_PLAN)
                    break

    def test_initial_side_tilt_and_acceleration_or_timestamp_faults_are_not_filtered_away(self):
        a=PitchEstimator(CAL,fuse_roll=True).update(frame(.01,[1,-.2,0]))
        with self.assertRaisesRegex(Fault,'body_tilt_stop'):
            SelfRightingController().validate_arm(a,{0:0.,1:0.},SELF_RIGHT_PLAN)
        for magnitude in (.4,1.6):
            estimator=PitchEstimator(CAL,fuse_roll=True)
            estimator.update(frame(.01,[1,0,0]))
            with self.assertRaisesRegex(Fault,'acceleration_outside_test_window'):
                estimator.update(frame(.02,[magnitude,0,0]))
        estimator=PitchEstimator(CAL,fuse_roll=True);estimator.update(frame(.01,[1,0,0]))
        with self.assertRaisesRegex(Fault,'imu_sample_gap'):
            estimator.update(frame(.05,[1,0,0]))


if __name__=='__main__':
    unittest.main()
