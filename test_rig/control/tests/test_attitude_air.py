from contextlib import redirect_stdout
import copy
import io
import math
import struct
import unittest
from unittest.mock import patch

from attitude import AIR_PLAN, Fault, PitchEstimator, air_command, validate_calibration
from air_trial import run, main, torque_packet
from protocol import RATIO, crc32_words
from test_wheel_check import Bus


CAL=dict(up_axis_raw=[0,0,1],forward_gravity_axis_raw=[1,0,0],
         positive_pitch_gyro_axis_raw=[0,-1,0],gyro_bias_dps=[0,0,0],
         gyro_sign_dynamic_check='PASS',wheel_signs={'0':1,'1':-1})


class IMU:
    def __init__(self,bus,fail=False,delay=False):
        self.bus=bus;self.fail=fail;self.delay=delay
    def sample(self):
        self.bus.sleep(.01)
        if self.fail and self.bus.t>3:
            raise OSError('injected_i2c_fault')
        if self.delay and self.bus.t>3:
            self.bus.sleep(.03)
        t=self.bus.t
        pitch=min(5,max(0,(t-1)*5))
        rate=5 if 1<t<2 else 0
        return dict(t_read_complete=t,accel_g=[math.sin(math.radians(pitch)),0,math.cos(math.radians(pitch))],
                    gyro_dps=[0,-rate,0])


class AirTests(unittest.TestCase):
    def run_case(self,fail=False,delay=False,exchange_transform=None):
        bus=Bus(timeout=True);imu=IMU(bus,fail,delay);report={}
        exchanges={m:bus.exchange(m) for m in (0,1)}
        if exchange_transform:
            exchanges=exchange_transform(exchanges,bus)
        run(exchanges,imu,copy.deepcopy(CAL),report,True,now=bus.now,sleep=bus.sleep,display=lambda s:None)
        return bus,report

    def test_default_no_io(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_reject_unvalidated_calibration(self):
        for change in ({'gyro_sign_dynamic_check':'NOT_TESTED'},{'wheel_signs':'NOT_TESTED'},
                       {'positive_pitch_gyro_axis_raw':[0,1,0]}):
            cal=dict(CAL,**change)
            with self.assertRaises(Fault):validate_calibration(cal)

    def test_packet_cap_crc_and_zero_other_terms(self):
        for value in (-.08,-.001,0,.001,.08):
            packet=torque_packet(1,value)
            torque,speed,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
            self.assertLessEqual(abs(torque/256000*RATIO),.08)
            self.assertEqual((speed,pos,kp),(0,0,0))
            decoded_kd=kd/128000000*RATIO**2
            self.assertGreater(decoded_kd,0)
            self.assertLessEqual(decoded_kd,AIR_PLAN['native_wheel_damping_nm_per_rad_s'])
            self.assertEqual(packet[2],0x91)
            self.assertEqual(struct.unpack_from('<I',packet,16)[0],crc32_words(packet[:16]))
        for value in (-.081,.081,float('nan')):
            with self.assertRaises(Fault):torque_packet(0,value)

    def test_forward_backward_pd_sign_and_tilt_cutoff(self):
        for pitch in (-5,5):
            cmd=air_command(dict(pitch_deg=pitch,pitch_rate_dps=0,roll_deg=0),{0:0,1:0})
            self.assertTrue(all(v*pitch>0 for v in cmd.values()))
        with self.assertRaisesRegex(Fault,'body_tilt'):
            air_command(dict(pitch_deg=26,pitch_rate_dps=0,roll_deg=0),{0:0,1:0})
        with self.assertRaisesRegex(Fault,'wheel_speed'):
            air_command(dict(pitch_deg=0,pitch_rate_dps=0,roll_deg=0),{0:2,1:0})

    def test_delayed_velocity_is_not_a_second_host_damper(self):
        a=dict(pitch_deg=3,pitch_rate_dps=0,roll_deg=0)
        self.assertEqual(air_command(a,{0:0,1:0}),air_command(a,{0:.1,1:-.1}))

    def test_reversal_predicted_net_torque_is_bounded(self):
        for pitch in (-10,10):
            for speed in (-.5,0,.5):
                cmd=air_command(dict(pitch_deg=pitch,pitch_rate_dps=0,roll_deg=0),{0:speed,1:speed})
                for value in cmd.values():
                    self.assertLessEqual(abs(value-AIR_PLAN['native_wheel_damping_nm_per_rad_s']*speed),.080000001)
                    self.assertLessEqual(abs(value),.08)

    def test_full_run_maps_both_wheels_and_stops(self):
        bus,report=self.run_case()
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(report['balanced_operation'],'NOT_TESTED')
        samples=report['samples']
        self.assertGreater(len(samples),990)
        last=samples[-1]['wheels']
        self.assertGreater(last[0]['command_protocol_nm'],0)
        self.assertLess(last[1]['command_protocol_nm'],0)

    def test_sensor_failure_or_stale_frame_stops_both(self):
        for fail,delay in ((True,False),(False,True)):
            bus,report=self.run_case(fail,delay)
            self.assertEqual(report['status'],'FAIL')
            self.assertTrue(report['final_disabled_verified'])
            last_pd=max(i for i,(_,_,phase) in enumerate(bus.log) if phase=='air_pd')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[last_pd+1:]))

    def test_peer_delay_cannot_send_second_stale_torque(self):
        def transform(exchanges,bus):
            original=exchanges[0]
            def delayed(packet,phase):
                result=original(packet,phase)
                if phase=='air_pd':bus.sleep(.011)
                return result
            return {**exchanges,0:delayed}
        bus,report=self.run_case(exchange_transform=transform)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(report['reason'],'stale_sample_or_pair_deadline')
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual([mid for mid,_,phase in bus.log if phase=='air_pd'],[0])


if __name__=='__main__':
    unittest.main()
