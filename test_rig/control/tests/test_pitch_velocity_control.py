import copy
from contextlib import redirect_stdout,redirect_stderr
import io
import math
import struct
import unittest
from unittest.mock import patch

from attitude import Fault
from air_trial import run
from ground_hold_trial import HoldTravel
from test_attitude_air import CAL
from test_cued_balance import HandIMU,Indicator
from test_two_deck_heading import frame
from test_wheel_check import Bus
from two_deck_heading_hold import RelativeHeadingController
from two_deck_speed_damping import PLAN as BASE
from two_deck_pitch_velocity import PLAN,PitchFrameVelocityController,main


def sample(t,rate=0.):
    a=frame(t,{0:0.,1:0.})
    a.update(pitch_rate_dps=rate,
             wheel_feedback_received_monotonic={0:t-.003,1:t-.002})
    return a


class PitchVelocityControlTests(unittest.TestCase):
    def test_no_io_without_complete_unlock_and_only_coordinate_opt_in_changes(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')), \
             patch('air_trial.run',side_effect=AssertionError('motor I/O')), \
             redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            self.assertEqual(main([]),0)
            with self.assertRaises(SystemExit):main(['--run-two-deck-pitch-velocity','--operator-ready'])
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
            {'name','control_phase','active_message','use_wheel_feedback_timestamps',
             'use_pitch_corrected_velocity'})

    def test_zero_body_rate_preserves_legacy_packet_bytes(self):
        new=PitchFrameVelocityController();old=RelativeHeadingController()
        for i in range(1,401):
            t=i*.005;a=sample(t);a.update(pitch_deg=.3*math.sin(2*t),pitch_error_deg=.3*math.sin(2*t))
            b=copy.deepcopy(a);speeds={0:math.sin(3*t),1:math.sin(3*t+.1)}
            nc=new(a,speeds,PLAN);oc=old(b,speeds,BASE)
            self.assertEqual(nc,oc)
            for m,sign in ((0,1),(1,-1)):
                self.assertEqual(new.allocated_torque_packet(m,sign,nc[m],PLAN),
                                 old.allocated_torque_packet(m,sign,oc[m],BASE))

    def test_known_stationary_world_wheel_cancels_body_relative_rotation(self):
        # Forward body rate is +1rad/s while wheels are stationary in world:
        # axle encoders must report -1rad/s. One warmup frame is explicit.
        c=PitchFrameVelocityController()
        for i in range(1,241):
            a=sample(i*.005,math.degrees(1.));c(a,{0:-1.,1:-1.},PLAN)
            d=a['velocity_frame_control']
            if i==1:
                self.assertTrue(d['first_sample_raw_warmup'])
            else:
                self.assertAlmostEqual(d['selected_control_proxy_m_s'],0.,places=14)
                self.assertEqual(a['velocity_hold']['encoder_velocity_proxy_m_s'],-.04)
            # The NET allocator and guards must still use RAW shaft rate.
            self.assertEqual(a['ardupilot_balance']['wheel_rate_forward_rad_s'],{0:-1.,1:-1.})
        self.assertLess(abs(a['velocity_hold']['pitch_reference_deg']),1e-9)
        c.reset();a=sample(2.,math.degrees(1.));c(a,{0:-1.,1:-1.},PLAN)
        self.assertTrue(a['velocity_frame_control']['first_sample_raw_warmup'])
        self.assertTrue(a['ardupilot_balance']['filter_reset'])

    def test_different_encoder_times_interpolate_pitch_rate_and_keep_exact_caps(self):
        c=PitchFrameVelocityController()
        c(sample(.005,0.),{0:0.,1:0.},PLAN)
        a=sample(.010,math.degrees(2.));commands=c(a,{0:.2,1:-.2},PLAN)
        d=a['velocity_frame_control']
        self.assertAlmostEqual(d['aligned_pitch_rate_rad_s'][0],.8)
        self.assertAlmostEqual(d['aligned_pitch_rate_rad_s'][1],1.2)
        self.assertAlmostEqual(d['selected_control_proxy_m_s'],.04)
        self.assertLess(a['velocity_hold']['pitch_reference_deg'],0.)
        for i in range(3,803):
            t=i*.005;a=sample(t,100*math.sin(t*7))
            a.update(pitch_deg=8*math.sin(t),pitch_error_deg=8*math.sin(t))
            commands=c(a,{0:5.9*math.sin(t),1:5.9*math.sin(t+.1)},PLAN)
            self.assertLessEqual(abs(a['velocity_hold']['pitch_reference_deg']),3.)
            for m,sign in ((0,1),(1,-1)):
                packet=c.allocated_torque_packet(m,sign,commands[m],PLAN)
                raw=struct.unpack_from('<h',packet,4)[0]
                self.assertEqual(raw,sign*a['ardupilot_balance']['exact_forward_ff_raw'][m])
                self.assertLessEqual(abs(commands[m]),.12)
                self.assertLessEqual(abs(a['ardupilot_balance']['predicted_net_forward_nm'][m]),.12+1e-12)

    def test_bad_frame_data_faults_and_cannot_mask_raw_speed_guard(self):
        mutations=[({},'both_wheel_samples_required'),
                   ({0:.02,1:.008},'stale_or_future_wheel_sample'),
                   ({0:.004,1:.008},'wheel_sample_before_imu_bracket'),
                   ({0:float('nan'),1:.008},'nonfinite_sample')]
        for timestamps,reason in mutations:
            c=PitchFrameVelocityController();c(sample(.005),{0:0.,1:0.},PLAN)
            a=sample(.01);a['wheel_feedback_received_monotonic']=timestamps
            with self.assertRaisesRegex(Fault,reason):c(a,{0:0.,1:0.},PLAN)
        c=PitchFrameVelocityController();c(sample(.005),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            c(sample(.01),{0:0.,1:0.},dict(PLAN,nominal_wheel_radius_m=.041))
        with self.assertRaisesRegex(Fault,'wheel_speed'):
            # Even if body pitch correction would cancel the mean velocity.
            PitchFrameVelocityController()(sample(.005,-100.),{0:6.1,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'explicit_timestamped_opt_in'):
            PitchFrameVelocityController()(sample(.005),{0:0.,1:0.},BASE)

    def test_runner_stale_feedback_stops_both_without_an_automatic_restart(self):
        for inject_stale in (False,True):
            bus=Bus(timeout=True);report={};cue=Indicator(bus)
            def tick():cue.check();cue.ticks+=1
            cue.tick=tick
            def exchange(mid):
                original=bus.exchange(mid)
                def call(packet,phase):
                    row=original(packet,phase)
                    row['feedback_received_monotonic']=bus.now()
                    if inject_stale and phase==PLAN['control_phase'] and cue.ticks>5:
                        row['feedback_received_monotonic']-=.1
                    return row
                return call
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=PitchFrameVelocityController(),travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(report['status'],'FAIL' if inject_stale else 'PASS',report.get('reason'))
            if inject_stale:self.assertEqual(report['reason'],'pitch_velocity_stale_or_future_wheel_sample')
            self.assertTrue(report['final_disabled_verified']);self.assertTrue(cue.off)
            stop=next(i for i,(_,_,p) in enumerate(bus.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[stop:]))


if __name__=='__main__':unittest.main()
