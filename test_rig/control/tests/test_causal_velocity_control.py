import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_quiet_baseline import PLAN as BASE,PitchFramePositionReturnLiveController
from two_deck_live_causal_velocity import PLAN,CausalVelocityLiveController,main


class CausalVelocityControlTests(unittest.TestCase):
    def test_inert_and_explicit_one_input_comparison_with_current_gains(self):
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
            {'name','ap_kd','use_causal_rotor_pitch_velocity','causal_velocity_window_s','active_message'})
        self.assertEqual(gains(PLAN),dict(pitch_p=2.75,pitch_i=.6,pitch_d=.065,speed_p=.25))
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_zero_velocity_wire_parity_and_raw_faults(self):
        equivalent=dict(BASE,ap_kd=PLAN['ap_kd'])
        a=CausalVelocityLiveController(TuningChannel(gains(PLAN)))
        b=PitchFramePositionReturnLiveController(TuningChannel(gains(equivalent)))
        for i in range(1,1201):
            x=sample(i*.005);x.update(pitch_deg=.2,pitch_error_deg=.2,pitch_rate_dps=0.,wheel_position_forward_rad={0:0.,1:0.})
            y=copy.deepcopy(x);ca=a(x,{0:0.,1:0.},PLAN);cb=b(y,{0:0.,1:0.},equivalent)
            self.assertEqual(ca,cb)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(a.allocated_torque_packet(mid,sign,ca[mid],PLAN),
                                 b.allocated_torque_packet(mid,sign,cb[mid],equivalent))
        self.assertTrue(a.speed_reference.estimator.ever_ready)
        for speeds,times in [({0:6.1,1:0.},None),({0:0.,1:0.},{0:5.,1:5.})]:
            x=sample(6.005);x['wheel_position_forward_rad']={0:0.,1:0.}
            if times is not None:x['wheel_feedback_received_monotonic']=times
            with self.assertRaises(Fault):a(x,speeds,PLAN)

    def test_full_harness_legacy_arm_fresh_estimator_and_final_disabled(self):
        bus=Bus(timeout=True);ch=TuningChannel(gains(PLAN),now=bus.now);c=CausalVelocityLiveController(ch);r={}
        class Cue:
            ticks=0;off=False
            def check(self):pass
            def tick(self):self.ticks+=1
            def deactivate(self):self.off=True
        cue=Cue()
        def exchange(mid):
            original=bus.exchange(mid)
            def call(packet,phase):
                row=original(packet,phase);row['feedback_received_monotonic']=bus.now();return row
            return call
        run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),r,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(PLAN,duration_s=.5),
            controller=c,travel_factory=HoldTravel,indicator=cue)
        self.assertEqual(r['status'],'PASS',r.get('reason'));self.assertTrue(r['final_disabled_verified'])
        self.assertTrue(r['controller_reset_before_active']);self.assertTrue(cue.off)
        self.assertTrue(c.speed_reference.estimator.ever_ready)
        self.assertEqual(ch.status()['phase'],'STOPPED')
        with self.assertRaises(Fault):c.reset()


if __name__=='__main__':unittest.main()
