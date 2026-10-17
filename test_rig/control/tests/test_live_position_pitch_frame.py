import copy
from contextlib import redirect_stdout
import io
import math
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains,with_gains
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_position_return import PLAN as BASE,PositionReturnLiveController
from two_deck_live_position_pitch_frame import PLAN,PitchFramePositionReturnLiveController,main


class PitchFramePositionLiveTests(unittest.TestCase):
    def controller(self):return PitchFramePositionReturnLiveController(TuningChannel(gains(PLAN)))

    def test_only_frame_and_finite_duration_changes_no_default_io(self):
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
            {'name','duration_s','active_message','use_pitch_corrected_velocity'})
        self.assertEqual(PLAN['duration_s'],1800.)
        self.assertTrue(PLAN['half_hour_live_session'])
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_zero_pitch_rate_preserves_v152_commands_and_position_origin(self):
        c=self.controller();b=PositionReturnLiveController(TuningChannel(gains(BASE)))
        for i in range(1,1201):
            t=i*.005;a=sample(t);a.update(pitch_rate_dps=0.,
                wheel_position_forward_rad={0:100.+.1*math.sin(t),1:-200.+.1*math.sin(t)})
            z=copy.deepcopy(a);speeds={0:.2*math.sin(t*3),1:.3*math.cos(t*4)}
            ca=c(a,speeds,PLAN);cb=b(z,speeds,BASE)
            self.assertEqual(ca,cb);self.assertEqual(c.position_origin,b.position_origin)
            self.assertEqual(a['position_hold'],z['position_hold'])
            for m,sign in ((0,1),(1,-1)):
                self.assertEqual(c.allocated_torque_packet(m,sign,ca[m],PLAN),
                                 b.allocated_torque_packet(m,sign,cb[m],BASE))

    def test_fixed_world_wheel_case_rotation_removed_only_from_speed_reference(self):
        c=self.controller()
        for i in range(1,241):
            a=sample(i*.005);a['pitch_rate_dps']=math.degrees(1.)
            a['wheel_position_forward_rad']={0:0.,1:0.}
            c(a,{0:-1.,1:-1.},PLAN)
            if i>1:self.assertAlmostEqual(a['velocity_frame_control']['selected_control_proxy_m_s'],0.,places=14)
            self.assertEqual(a['ardupilot_balance']['wheel_rate_forward_rad_s'],{0:-1.,1:-1.})
            self.assertEqual(a['position_velocity_target_m_s'],0.)
        self.assertLess(abs(a['speed_pitch_reference_deg']),1e-9)
        with self.assertRaisesRegex(Fault,'wheel_speed'):
            a=sample(1.205);a['pitch_rate_dps']=-200.
            c(a,{0:6.1,1:0.},PLAN)

    def test_position_return_and_timestamp_rejection_keep_original_budgets(self):
        c=self.controller();c(sample(.005),{0:0.,1:0.},PLAN)
        for i in range(2,402):
            a=sample(i*.005);a['pitch_rate_dps']=20.*math.sin(i*.05)
            a['wheel_position_forward_rad']={0:.5,1:.5}
            commands=c(a,{0:.1,1:.2},PLAN)
            self.assertLess(a['position_velocity_target_m_s'],0.)
            for m,sign in ((0,1),(1,-1)):
                c.allocated_torque_packet(m,sign,commands[m],PLAN)
                self.assertLessEqual(abs(c.allocations[m].feedforward_nm),.12+1e-12)
                self.assertLessEqual(abs(c.allocations[m].predicted_net_nm),.12+1e-12)
        for mutation in ({},{0:2.004,1:2.008},{0:1.9,1:1.9}):
            c=self.controller();c(sample(2.),{0:0.,1:0.},PLAN)
            a=sample(2.005);a['wheel_feedback_received_monotonic']=mutation
            with self.assertRaisesRegex(Fault,'pitch_velocity_'):c(a,{0:0.,1:0.},PLAN)

    def test_live_update_preserves_origin_pid_and_both_velocity_states(self):
        c=self.controller()
        for i in range(1,201):c(sample(i*.005),{0:.1,1:.1},PLAN)
        pid=c.pid;ref=c.speed_reference;estimator=ref.frame_estimator
        before=(c.position_origin,c.position_configuration,ref.filtered_velocity,
                ref.pitch_reference_deg,estimator.previous,c.pid.integrator,c.pid.error,c.pid.derivative)
        c.apply_live_gains(PLAN,with_gains(PLAN,dict(gains(PLAN),pitch_p=3.)))
        self.assertIs(c.pid,pid);self.assertIs(c.speed_reference,ref)
        self.assertIs(c.speed_reference.frame_estimator,estimator)
        self.assertEqual(before,(c.position_origin,c.position_configuration,ref.filtered_velocity,
                ref.pitch_reference_deg,estimator.previous,c.pid.integrator,c.pid.error,c.pid.derivative))
        with self.assertRaisesRegex(Fault,'cannot_reset'):c.reset()

    def fixture(self,stale):
        class Cue:
            def __init__(self):self.off=False
            def tick(self):pass
            def check(self):pass
            def deactivate(self):self.off=True
        bus=Bus(timeout=True);report={};cue=Cue();ch=TuningChannel(gains(PLAN),now=bus.now);count=[0]
        def exchange(mid):
            original=bus.exchange(mid)
            def wrapped(packet,phase):
                row=original(packet,phase);row['feedback_received_monotonic']=bus.now()
                if mid==1 and phase==PLAN['control_phase']:count[0]+=1
                if stale and count[0]>=30 and phase==PLAN['control_phase']:
                    row['feedback_received_monotonic']-=.1
                return row
            return wrapped
        run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=PitchFramePositionReturnLiveController(ch),travel_factory=HoldTravel,indicator=cue)
        return bus,report,ch,cue

    def test_finite_run_and_stale_feedback_stop_both_without_rearm(self):
        for stale in (False,True):
            b,r,ch,cue=self.fixture(stale)
            self.assertEqual(r['status'],'FAIL' if stale else 'PASS',r.get('reason'))
            if stale:self.assertIn('stale',r['reason'])
            self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
            self.assertEqual(ch.status()['phase'],'STOPPED')
            self.assertTrue(all(w['feedback']['mode']==1 for s in r['samples'] for w in s['wheels'].values()))
            stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
