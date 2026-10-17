import math
import unittest

from causal_rotor_pitch_velocity import CausalRotorPitchVelocity


class CausalRotorPitchTests(unittest.TestCase):
    def test_constant_world_rate_both_directions_with_body_rotation_and_host_skew(self):
        for rate in (-.2,0.,.2):
            c=CausalRotorPitchVelocity();ready=[]
            for i in range(1,401):
                t=i*.005;times={0:t-.003,1:t-.001}
                positions={m:100.+(rate-.4)*rt for m,rt in times.items()}
                r=c.update(t,math.degrees(.4*t),positions,times,{0:rate-.4,1:rate-.4})
                if r['ready']:ready.append(r['corrected_proxy_m_s'])
            self.assertGreater(len(ready),390)
            self.assertLess(max(abs(v-.04*rate) for v in ready),1e-12)

    def test_fixed_world_rocking_body_cancels_without_using_reported_rate_filter(self):
        c=CausalRotorPitchVelocity();new=[];mixed=[]
        theta=lambda t:.1*math.sin(math.tau*2.*t)
        gyro=lambda t:.1*math.tau*2.*math.cos(math.tau*2.*t)
        for i in range(1,2001):
            t=i*.005;times={0:t-.003,1:t-.001}
            reported={m:-gyro(rt-.03) for m,rt in times.items()}
            r=c.update(t,math.degrees(theta(t)),{m:-theta(rt) for m,rt in times.items()},times,reported)
            if r['ready']:
                new.append(r['corrected_proxy_m_s']);mixed.append(.04*(sum(reported.values())/2+gyro(t)))
        rms=lambda a:math.sqrt(sum(v*v for v in a)/len(a))
        self.assertLess(rms(new),rms(mixed)/50)

    def test_strict_time_and_finite_fields_and_no_fallback_after_ready(self):
        for mutate in [lambda a:a.update(t=1.),lambda a:a['received_times'].update({0:1.}),
                       lambda a:a['positions'].update({1:float('nan')}),
                       lambda a:a['reported_speeds'].pop(1)]:
            c=CausalRotorPitchVelocity()
            for i in range(1,20):
                t=i*.005;c.update(t,0.,{0:0.,1:0.},{0:t-.003,1:t-.001},{0:0.,1:0.})
            self.assertTrue(c.ever_ready)
            a=dict(t=.1,pitch_deg=0.,positions={0:0.,1:0.},received_times={0:.097,1:.099},reported_speeds={0:0.,1:0.})
            mutate(a)
            with self.assertRaises(ValueError):c.update(**a)

    def test_reported_velocity_does_not_replace_position_secant_and_history_is_bounded(self):
        a=CausalRotorPitchVelocity();b=CausalRotorPitchVelocity()
        for i in range(1,2001):
            t=i*.005;args=(t,math.sin(t),{0:math.sin(t-.003),1:math.sin(t-.001)},
                          {0:t-.003,1:t-.001},{0:0.,1:0.})
            x=a.update(*args);y=b.update(*args[:-1],{0:2.,1:-1.})
            if x['ready']:self.assertEqual(x['corrected_proxy_m_s'],y['corrected_proxy_m_s'])
            self.assertTrue(all(len(h)<=7 for h in a.history.values()))
        self.assertFalse(hasattr(a,'motor'))


if __name__=='__main__':unittest.main()
