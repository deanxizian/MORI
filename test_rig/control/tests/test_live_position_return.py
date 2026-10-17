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
from live_tuning_policy import gains,with_gains,validate_plan_change
from stationary_integral import StationaryIntegralLiveController
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_position_return import PLAN,PositionReturnLiveController,main
from two_deck_live_stationary_integral import PLAN as BASE


class LivePositionReturnTests(unittest.TestCase):
    def controller(self):return PositionReturnLiveController(TuningChannel(gains(PLAN)))

    def test_inert_default_and_original_limits_non_smax_path(self):
        old=with_gains(BASE,dict(gains(BASE),pitch_d=.070))
        changed={k for k in set(old)|set(PLAN) if old.get(k)!=PLAN.get(k)}
        self.assertEqual(changed,{'name','active_message','allow_position_velocity_target',
            'position_speed_kp_per_s','position_speed_limit_m_s'})
        self.assertEqual(PLAN.get('ap_smax',0.),0.)
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        with self.assertRaises(ValueError):
            validate_plan_change(PLAN,dict(PLAN,position_speed_kp_per_s=.4))

    def test_zero_common_error_preserves_original_motor_packets_and_filters(self):
        old=with_gains(BASE,dict(gains(BASE),pitch_d=.070))
        c=self.controller();b=StationaryIntegralLiveController(TuningChannel(gains(old)))
        for i in range(1,1001):
            a=sample(i*.005)
            a.update(wheel_position_forward_rad={0:100.+i/1024.,1:-200.-i/1024.},
                     pitch_deg=.2+.5*math.sin(i*.04),pitch_error_deg=.2+.5*math.sin(i*.04),
                     pitch_rate_dps=4*math.cos(i*.04))
            z=copy.deepcopy(a);speeds={0:.2,1:-.2}
            ca=c(a,speeds,PLAN);cb=b(z,speeds,old)
            self.assertEqual(a['position_velocity_target_m_s'],0.)
            self.assertEqual(a['velocity_hold'],z['velocity_hold'])
            self.assertEqual(a['ardupilot_balance'],z['ardupilot_balance'])
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(c.allocated_torque_packet(mid,sign,ca[mid],PLAN),
                                 b.allocated_torque_packet(mid,sign,cb[mid],old))
        self.assertIsNone(c.pid.slew)

    def test_signed_drift_return_cap_and_budget_with_nonzero_origins(self):
        for displacement in (-.30,-.01,.01,.30):
            c=self.controller();a=sample(.005)
            a['wheel_position_forward_rad']={0:10.,1:-20.};c(a,{0:0.,1:0.},PLAN)
            self.assertEqual(a['position_velocity_target_m_s'],0.)
            origin=c.position_origin
            for i in range(2,102):
                a=sample(i*.005);a['wheel_position_forward_rad']={
                    0:10.+displacement/.04,1:-20.+displacement/.04}
                a.update(pitch_deg=.2,pitch_error_deg=.2,pitch_rate_dps=0.)
                result=c(a,{0:0.,1:0.},PLAN)
                target=a['position_velocity_target_m_s']
                self.assertLess(target*displacement,0.)
                self.assertLessEqual(abs(target),.03)
                self.assertAlmostEqual(target,max(-.03,min(.03,-.30*displacement)))
                self.assertGreater(a['speed_pitch_reference_deg']*target,0.)
                for mid,sign in ((0,1),(1,-1)):
                    c.allocated_torque_packet(mid,sign,result[mid],PLAN)
                    self.assertLessEqual(abs(c.allocations[mid].feedforward_nm),.12+1e-12)
                    self.assertLessEqual(abs(c.allocations[mid].predicted_net_nm),.12+1e-12)
            self.assertEqual(c.position_origin,origin)

    def test_missing_or_changed_positions_fault_before_command_and_no_active_origin_reset(self):
        c=self.controller();a=sample(.005);a.pop('wheel_position_forward_rad')
        with self.assertRaisesRegex(Fault,'requires_both_encoders'):c(a,{0:0.,1:0.},PLAN)
        self.assertEqual(c.allocations,{})
        c=self.controller();c(sample(.005),{0:0.,1:0.},PLAN)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            c(sample(.010),{0:0.,1:0.},dict(PLAN,position_speed_kp_per_s=.31))
        with self.assertRaisesRegex(Fault,'cannot_reset'):c.reset()
        c=self.controller()
        with self.assertRaisesRegex(Fault,'wheel_speed'):c(sample(.005),{0:7.,1:0.},PLAN)
        self.assertIsNone(c.position_origin)

    def test_live_gain_changes_preserve_origin_integrator_and_reference_state(self):
        c=self.controller()
        for i in range(1,201):
            a=sample(i*.005);a['wheel_position_forward_rad']={0:i*.001,1:i*.001}
            c(a,{0:.1,1:.1},PLAN)
        pid=c.pid;origin=c.position_origin
        before=(c.position_configuration,c.speed_reference.filtered_velocity,
                c.speed_reference.pitch_reference_deg,c.pid.integrator,c.pid.error,c.pid.derivative)
        changed=with_gains(PLAN,dict(gains(PLAN),pitch_p=3.))
        c.apply_live_gains(PLAN,changed)
        self.assertIs(c.pid,pid);self.assertEqual(c.position_origin,origin)
        self.assertEqual(before,(c.position_configuration,c.speed_reference.filtered_velocity,
                c.speed_reference.pitch_reference_deg,c.pid.integrator,c.pid.error,c.pid.derivative))

    def fixture(self,fault):
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
                return row
            return wrapped
        class IMU(HandIMU):
            def sample(self):
                s=super().sample()
                if fault and count[0]>=30:s['gyro_dps'][1]=500.
                return s
        run({m:exchange(m) for m in (0,1)},IMU(bus),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=PositionReturnLiveController(ch),travel_factory=HoldTravel,indicator=cue)
        return bus,report,ch,cue

    def test_mode1_run_and_fault_both_end_disabled_without_rearm(self):
        for fault in (False,True):
            b,r,ch,cue=self.fixture(fault)
            self.assertEqual(r['status'],'FAIL' if fault else 'PASS',r.get('reason'))
            if fault:self.assertIn('rate',r['reason'])
            self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
            self.assertTrue(all(w['feedback']['mode']==1 for s in r['samples'] for w in s['wheels'].values()))
            self.assertEqual(ch.status()['phase'],'STOPPED')
            self.assertIn('position_error_proxy_m',ch.status())
            stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in b.log[stop:]))


if __name__=='__main__':unittest.main()
