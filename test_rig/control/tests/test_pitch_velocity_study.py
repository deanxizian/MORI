import math
import unittest

from offline_after24_20261017.pitch_velocity_proxy import PitchVelocityProxy


class PitchVelocityStudyTests(unittest.TestCase):
    def test_fixed_wheel_chassis_rotation_cancels_both_directions(self):
        for rate in (-30.,30.):
            estimator=PitchVelocityProxy()
            w=-math.radians(rate)
            first=estimator.update(1.,rate,{0:w,1:w},{0:.999,1:.999})
            self.assertFalse(first['ready']);self.assertIsNone(first['corrected_proxy_m_s'])
            result=estimator.update(1.005,rate,{0:w,1:w},{0:1.002,1:1.003})
            self.assertAlmostEqual(result['corrected_proxy_m_s'],0.,places=12)
            self.assertNotEqual(result['raw_proxy_m_s'],0.)

    def test_translation_and_opposing_turn_rate_are_separated(self):
        estimator=PitchVelocityProxy();rate=.3;speed=.1
        speeds={0:speed/.04-rate+.7,1:speed/.04-rate-.7}
        estimator.update(1.,math.degrees(rate),speeds,{0:.999,1:.999})
        result=estimator.update(1.005,math.degrees(rate),speeds,{0:1.002,1:1.003})
        self.assertAlmostEqual(result['corrected_proxy_m_s'],speed)

    def test_individual_timestamp_interpolation_avoids_using_newer_gyro(self):
        estimator=PitchVelocityProxy()
        estimator.update(1.,10.,{0:0.,1:0.},{0:.999,1:.999})
        # Linear10->20deg/s; feedback at40%/60% of the5ms interval.
        result=estimator.update(1.005,20.,{0:-math.radians(14),1:-math.radians(16)},
                                {0:1.002,1:1.003})
        self.assertAlmostEqual(result['corrected_proxy_m_s'],0.,places=12)

    def test_missing_nonfinite_stale_future_and_unbracketed_data_rejected(self):
        for speeds,times in [({0:0.},{0:.999,1:.999}),
                ({0:float('nan'),1:0.},{0:.999,1:.999}),
                ({0:0.,1:0.},{0:.98,1:.999}),({0:0.,1:0.},{0:1.001,1:.999})]:
            with self.assertRaises(ValueError):PitchVelocityProxy().update(1.,0.,speeds,times)
        for t,times in [(1.,{0:.999,1:.999}),(1.005,{0:.999,1:1.003}),
                        (1.03,{0:1.029,1:1.029})]:
            estimator=PitchVelocityProxy();estimator.update(1.,0.,{0:0.,1:0.},{0:.999,1:.999})
            with self.assertRaises(ValueError):estimator.update(t,0.,{0:0.,1:0.},times)

    def test_no_rotation_leaves_encoder_proxy_unchanged(self):
        estimator=PitchVelocityProxy()
        estimator.update(1.,0.,{0:1.,1:2.},{0:.999,1:.999})
        result=estimator.update(1.005,0.,{0:1.,1:2.},{0:1.002,1:1.003})
        self.assertEqual(result['corrected_proxy_m_s'],result['raw_proxy_m_s'])


if __name__=='__main__':unittest.main()
