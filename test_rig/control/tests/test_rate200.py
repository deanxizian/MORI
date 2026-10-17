import copy
import io
import math
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from attitude import AIR_PLAN,Fault
from air_trial import run,control_rate_hz,imu_configuration
from self_righting_rate200 import PLAN,main
from self_righting_capture_velocity_window import PLAN as OLD
from test_wheel_check import Bus
from test_attitude_air import CAL


class RateIMU:
    def __init__(self,bus,step):self.bus,self.step=bus,step
    def sample(self):
        self.bus.sleep(self.step);t=self.bus.t
        pitch=min(5,max(0,(t-1)*5));rate=5 if 1<t<2 else 0
        return dict(t_read_complete=t,
            accel_g=[math.sin(math.radians(pitch)),0,math.cos(math.radians(pitch))],
            gyro_dps=[0,-rate,0])


class Rate200Tests(unittest.TestCase):
    def test_only_sensor_rate_changes(self):
        keys={'name','active_message','motion_hold_reason','imu_odr_hz'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in keys},
                         {k:v for k,v in OLD.items() if k not in keys})
        self.assertEqual(control_rate_hz(PLAN),200)
        self.assertEqual(PLAN['stable_duration_s'],30.)
        self.assertEqual(imu_configuration(PLAN),dict(bandwidth_divisor=4,odr_hz=200))

    def test_default_rate_preserved_and_invalid_rate_rejected(self):
        self.assertEqual(control_rate_hz(AIR_PLAN),100)
        self.assertEqual(imu_configuration(AIR_PLAN),dict(bandwidth_divisor=2))
        for bad in (True,200.,50,400,'200'):
            with self.assertRaisesRegex(Fault,'unsupported_control_imu_odr'):
                imu_configuration(dict(AIR_PLAN,imu_odr_hz=bad))

    def fixture(self,step):
        # Kinematic input/packet workflow fixture, not a physical plant model.
        bus=Bus(timeout=True);report={};p=dict(AIR_PLAN,imu_odr_hz=200,duration_s=1.)
        run({m:bus.exchange(m) for m in (0,1)},RateIMU(bus,step),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=p)
        return bus,report

    def test_200_workflow_keeps_final_stop_and_declared_rate(self):
        _,r=self.fixture(.005)
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['requested_control_hz'],200)
        self.assertGreaterEqual(r['control_cycles'],190)
        self.assertTrue(r['final_disabled_verified'])
        self.assertEqual(r['balanced_operation'],'NOT_TESTED')

    def test_old_cadence_cannot_pass_declared_200_rate(self):
        bus,r=self.fixture(.01)
        self.assertEqual(r['status'],'FAIL');self.assertEqual(r['reason'],'control_timing_incomplete')
        self.assertTrue(r['final_disabled_verified'])
        last=max(i for i,(_,_,phase) in enumerate(bus.log) if phase=='air_pd')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[last+1:]))

    def test_default_inert(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)


if __name__=='__main__':unittest.main()
