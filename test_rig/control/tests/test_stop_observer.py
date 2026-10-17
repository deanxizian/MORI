import io
import math
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

from air_trial import run
from attitude import AIR_PLAN
from preflight import RawIMU
from air_trial import main
from stop_observer import StopIMURecorder
from test_attitude_air import CAL,IMU
from test_wheel_check import Bus
from wheel_check import stop_both


class PassiveIMU(IMU):
    def sample_nowait(self):
        return dict(t_read_complete=self.bus.now(),accel_g=[0,0,1],gyro_dps=[0,0,0])


class StopObservationTests(unittest.TestCase):
    def test_both_lock_attempts_precede_observation_even_if_one_fails(self):
        bus=Bus(fail=lambda mid,p,phase:mid==0 and phase=='stop_transition')
        report={};observed=[]
        def observe(phase):
            observed.append(phase)
            self.assertEqual([m for m,_,p in bus.log[:2] if p=='stop_transition'],[0,1])
            raise OSError('injected_observer_failure')
        stop_both({m:bus.exchange(m) for m in (0,1)},report,bus.now,bus.sleep,observer=observe)
        self.assertTrue(observed)
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(bus.maximum_enabled,0)
        self.assertTrue(all((p[2]>>4)&7==0 for _,p,_ in bus.log))

    def test_tail_records_after_stop_and_never_writes_to_bus(self):
        bus=Bus();report={};imu=PassiveIMU(bus)
        recorder=StopIMURecorder(imu,report,.1,bus.now,bus.sleep)
        stop_both({m:bus.exchange(m) for m in (0,1)},report,bus.now,bus.sleep,observer=recorder.poll)
        count=len(bus.log);recorder.finish()
        self.assertEqual(len(bus.log),count)
        self.assertEqual(recorder.data['status'],'PASS')
        self.assertEqual(recorder.data['motor_commands_sent'],0)
        self.assertEqual({s['phase'] for s in recorder.data['samples']},
                         {'after_both_lock_attempts','lock_confirmation','after_lock_verified'})

    def test_unconfirmed_stop_does_not_delay_cutoff_report(self):
        bus=Bus();report={'final_disabled_verified':False}
        recorder=StopIMURecorder(PassiveIMU(bus),report,2,bus.now,bus.sleep)
        recorder.finish()
        self.assertEqual(bus.now(),0)
        self.assertEqual(recorder.data['status'],'NOT_TESTED')

    def test_bad_imu_does_not_suppress_stop_verification(self):
        bus=Bus();report={}
        imu=PassiveIMU(bus)
        imu.sample_nowait=lambda:(_ for _ in ()).throw(ValueError('saturation'))
        recorder=StopIMURecorder(imu,report,.1,bus.now,bus.sleep)
        stop_both({m:bus.exchange(m) for m in (0,1)},report,bus.now,bus.sleep,observer=recorder.poll)
        recorder.finish()
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(recorder.data['status'],'FAIL')
        self.assertTrue(recorder.data['errors'])

    def test_sensor_poll_does_not_wait_and_keeps_rejected_words(self):
        imu=RawIMU({});calls=[]
        imu.read=lambda reg,n=1:calls.append(reg) or (0,)
        with patch('preflight.time.sleep',side_effect=AssertionError('wait')):
            self.assertIsNone(imu.sample_nowait())
        self.assertEqual(calls,[2])
        words=(32767,0,0,0,0,0,0)
        imu.read=lambda reg,n=1:(0xc0,) if reg==2 else words
        with self.assertRaises(ValueError):imu.sample_nowait()
        self.assertEqual(imu.last_rejected_sample['raw_words'],list(words))

    def test_runner_fault_stops_then_observes_without_rearming(self):
        bus=Bus(fail=lambda mid,p,phase:mid==0 and phase=='air_pd');report={}
        run({m:bus.exchange(m) for m in (0,1)},PassiveIMU(bus),CAL,report,False,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(AIR_PLAN,post_stop_observation_s=.1))
        self.assertEqual(report['status'],'FAIL')
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(report['stop_imu_observation']['status'],'PASS')
        last=next(i for i,(_,_,p) in enumerate(bus.log) if p=='stop_transition')
        self.assertTrue(all((p[2]>>4)&7==0 for _,p,_ in bus.log[last:]))

    def test_retired_launch_profile_is_refused_before_hardware_io(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(['--run-air-trial'],plan=dict(AIR_PLAN,motion_hold_reason='Retired profile'))
        self.assertEqual(caught.exception.code,2)

    def test_invalid_observation_duration(self):
        for duration in (0,-1,3.01,float('nan')):
            with self.assertRaises(ValueError):StopIMURecorder(None,{},duration,None,None)


if __name__=='__main__':unittest.main()
