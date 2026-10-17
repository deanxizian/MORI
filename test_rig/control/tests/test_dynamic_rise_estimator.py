import math
import unittest
from attitude import Fault,PitchEstimator
from test_attitude_air import CAL
from air_trial import run
from ground_hold_trial import HoldTravel
from self_righting_lift_trial import LIFT_PLAN
from self_righting_trial import SelfRightingController
from test_self_righting import TraceIMU
from test_wheel_check import Bus


def frame(t,norm=1.,rate=0.,angle=90.):
    return dict(t_read_complete=t,
        accel_g=[norm*math.sin(math.radians(angle)),0,norm*math.cos(math.radians(angle))],
        gyro_dps=[0,-rate,0])


class DynamicRiseEstimatorTests(unittest.TestCase):
    def test_acceleration_does_not_tilt_dynamic_attitude_but_gyro_does(self):
        e=PitchEstimator(CAL,fuse_roll=True);e.update(frame(.01))
        for i in range(1,30):
            a=e.update(frame(.01+i*.01,angle=60.,rate=-10.),dynamic=True)
        self.assertAlmostEqual(a['pitch_deg'],87.1)
        self.assertEqual(a['gravity_correction_weight'],0.)
        with self.assertRaisesRegex(Fault,'static_initialization'):
            PitchEstimator(CAL).update(frame(.01),dynamic=True)

    def test_brief_moderate_transient_allowed_hard_and_sustained_events_reject(self):
        for n in (.3,1.7):
            e=PitchEstimator(CAL);e.update(frame(.01))
            e.update(frame(.02,n),dynamic=True)
            e.update(frame(.03),dynamic=True)
            self.assertIsNone(e.dynamic_outside_normal_since)
            with self.assertRaisesRegex(Fault,'sustained_dynamic'):
                for i in range(1,12):e.update(frame(.03+i*.01,n),dynamic=True)
        for n in (.1,3.,3.1):
            e=PitchEstimator(CAL);e.update(frame(.01))
            with self.assertRaisesRegex(Fault,'outside_dynamic'):
                e.update(frame(.02,n),dynamic=True)
        e=PitchEstimator(CAL);e.update(frame(.01))
        with self.assertRaisesRegex(Fault,'outside_test_window'):e.update(frame(.02,1.7))

    def test_runner_only_uses_dynamic_window_in_active_rise_and_stops_impact(self):
        for impact in (False,True):
            bus=Bus(timeout=True);report={};imu=TraceIMU(bus);sample=imu.sample
            def wrapped():
                raw=sample()
                if impact and any(phase=='self_righting' for _,_,phase in bus.log):
                    raw['accel_g']=[v*3.1 for v in raw['accel_g']]
                return raw
            imu.sample=wrapped
            run({m:bus.exchange(m) for m in (0,1)},imu,CAL,report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=LIFT_PLAN,
                controller=SelfRightingController(),travel_factory=HoldTravel)
            self.assertTrue(report['final_disabled_verified'])
            self.assertTrue(all(not s['attitude']['dynamic_acceleration_window'] for s in report['waiting_samples']))
            if impact:
                self.assertEqual(report['reason'],'acceleration_outside_dynamic_window')
                last=max(i for i,(_,_,phase) in enumerate(bus.log) if phase=='self_righting')
                self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[last+1:]))
            else:
                self.assertEqual(report['status'],'PASS',report.get('reason'))
                self.assertTrue(report['samples'][0]['attitude']['dynamic_acceleration_window'])
                self.assertFalse(report['samples'][-1]['attitude']['dynamic_acceleration_window'])


if __name__=='__main__':unittest.main()
