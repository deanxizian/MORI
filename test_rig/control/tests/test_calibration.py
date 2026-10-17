import math
import unittest
from calibration import angles, basis, pose


class CalibrationTests(unittest.TestCase):
    def test_physical_rotation_sign_and_zero(self):
        up=dict(accel_g_mean=[0,0,1],gyro_dps_mean=[.1,.2,.3])
        fwd=dict(accel_g_mean=[.5,0,math.sqrt(.75)])
        cal=basis(up,fwd)
        # With raw +Z up, body rotation about raw -Y moves the measured
        # gravity vector towards raw +X; rotation and accelerometer agree.
        sample=dict(accel_g=fwd['accel_g_mean'],gyro_dps=[.1,-9.8,.3])
        result=angles(sample,cal)
        self.assertAlmostEqual(result['pitch_accel_deg'],30)
        self.assertAlmostEqual(result['pitch_rate_dps'],10)
        self.assertAlmostEqual(angles(dict(accel_g=[0,0,1],gyro_dps=[.1,.2,.3]),cal)['pitch_accel_deg'],0)

    def test_motion_and_missing_data_cannot_be_zero(self):
        rows=[dict(elapsed_s=i*.01,imu=dict(accel_g=[0,0,1],gyro_dps=[0,10,0])) for i in range(400)]
        with self.assertRaisesRegex(ValueError,'no_stationary'):
            pose(rows)
        for row in rows:
            row['imu']['gyro_dps']=[.1,.1,.1]
        self.assertGreater(pose(rows)['samples'],190)
        with self.assertRaisesRegex(ValueError,'no_stationary'):
            pose(rows[::4])

    def test_uninformative_or_inverted_pose_rejected(self):
        up=dict(accel_g_mean=[0,0,1],gyro_dps_mean=[0,0,0])
        for a in ([0,0,1],[0,0,-1],[1,0,0]):
            with self.assertRaises(ValueError):
                basis(up,dict(accel_g_mean=a))


if __name__=='__main__':
    unittest.main()
