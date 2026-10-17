"""Packet/state safety checks for finite preparation; no plant simulation."""
import struct
import unittest

from air_trial import run,torque_packet,health
from attitude import Fault
from ground_hold_trial import HoldTravel
from protocol import RATIO
from self_righting_lift_trial import LIFT_PLAN
from self_righting_trial import SelfRightingController
from test_attitude_air import CAL
from test_self_righting import TraceIMU,pose
from test_wheel_check import Bus


class CounterRollTests(unittest.TestCase):
    def test_preparation_is_single_bounded_phase_and_packet_reversal_stays_in_envelope(self):
        for sign in (-1.,1.):
            c=SelfRightingController();c(pose(.01,88.*sign),{0:0.,1:0.},LIFT_PLAN)
            for i in range(1,80):
                a=pose(.01+i*.01,88.*sign)
                speeds={0:-2.*sign,1:-2.*sign}
                out=c(a,speeds,LIFT_PLAN)
                for m in (0,1):
                    ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(m,out[m],c.motor_plan(LIFT_PLAN)),4)
                    net=ff/256000*RATIO-kd/128000000*RATIO**2*speeds[m]
                    self.assertLessEqual(abs(net),LIFT_PLAN['predicted_net_torque_limit_nm']+1e-10)
                    self.assertLessEqual(abs(ff/256000*RATIO),LIFT_PLAN['feedforward_torque_limit_nm'])
                if c.phase=='PRE_ROLL':
                    self.assertLess(out[0]*sign,0.)
                    self.assertEqual(a['self_righting']['native_damping_compensation_fraction'],float(LIFT_PLAN.get('pre_roll_compensate_native_damping',False)))
                elif a['self_righting']['rise_elapsed_s']>.15:
                    self.assertGreater(net*sign,.30)
            self.assertEqual([e['phase'] for e in c.events],['PRE_ROLL','RISING'])
            self.assertLessEqual(c.events[1]['t']-c.events[0]['t'],LIFT_PLAN['pre_roll_duration_s']+.01)

    def test_counter_roll_compensation_is_bounded_and_default_remains_off(self):
        for sign in (-1.,1.):
            c=SelfRightingController();c(pose(.01,88.*sign),{0:0.,1:0.},LIFT_PLAN)
            for i in range(1,18):
                speeds={0:-3.*sign,1:-3.*sign};a=pose(.01+i*.01,88.*sign)
                out=c(a,speeds,LIFT_PLAN)
            self.assertEqual(c.phase,'PRE_ROLL')
            ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(0,out[0],c.motor_plan(LIFT_PLAN)),4)
            net=ff/256000*RATIO-kd/128000000*RATIO**2*speeds[0]
            self.assertAlmostEqual(net,-sign*LIFT_PLAN['pre_roll_torque_nm'],delta=RATIO/256000)
        with self.assertRaisesRegex(Fault,'invalid_pre_roll_compensation'):
            SelfRightingController().validate_arm(pose(.01),{0:0.,1:0.},dict(LIFT_PLAN,pre_roll_compensate_native_damping='yes'))

    def test_invalid_preparation_rejects_before_enable(self):
        for changed in ({'pre_roll_duration_s':-.1},{'pre_roll_duration_s':.6},
                        {'pre_roll_torque_nm':.6},{'pre_roll_speed_limit_rad_s':12.},
                        {'pre_roll_travel_limit_m':.5}):
            bus=Bus(timeout=True);report={}
            run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,stuck=True),CAL,report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(LIFT_PLAN,**changed),
                controller=SelfRightingController(),travel_factory=HoldTravel)
            self.assertEqual(report['reason'],'invalid_pre_roll_plan')
            self.assertEqual(bus.maximum_enabled,0)
            self.assertTrue(report['final_disabled_verified'])

    def test_preparation_speed_travel_and_wrong_way_fault_latch(self):
        for a,speeds,reason in (
            (pose(.02),{0:LIFT_PLAN['pre_roll_speed_limit_rad_s']+.1,1:0.},'pre_roll_speed_stop'),
            (pose(.02,positions={0:LIFT_PLAN['pre_roll_travel_limit_m']/LIFT_PLAN['nominal_wheel_radius_m']+.01,1:0.}),{0:0.,1:0.},'pre_roll_travel_stop'),
            (pose(.02,94.),{0:0.,1:0.},'wrong_way')):
            c=SelfRightingController();c(pose(.01),{0:0.,1:0.},LIFT_PLAN)
            with self.assertRaisesRegex(Fault,reason):c(a,speeds,LIFT_PLAN)
            with self.assertRaisesRegex(Fault,'fault_latched'):c(pose(.03),{0:0.,1:0.},LIFT_PLAN)

    def test_runner_both_phases_fault_stop_without_automatic_retry(self):
        for failure_at in (.15,LIFT_PLAN['pre_roll_duration_s']+.05):
            bus=Bus(timeout=True);report={};imu=TraceIMU(bus,stuck=True);sample=imu.sample
            start=[None];fault_index=[None]
            def wrapped():
                raw=sample()
                if any(phase=='self_righting' for _,_,phase in bus.log):
                    if start[0] is None:start[0]=bus.t
                    if bus.t-start[0]>=failure_at:
                        raw['gyro_dps']=[0,-(LIFT_PLAN.get('rise_pitch_rate_limit_dps',LIFT_PLAN['pitch_rate_limit_dps'])+1.),0];fault_index[0]=len(bus.log)
                return raw
            imu.sample=wrapped
            run({m:bus.exchange(m) for m in (0,1)},imu,CAL,report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=LIFT_PLAN,
                controller=SelfRightingController(),travel_factory=HoldTravel)
            self.assertEqual(report['reason'],'body_rotation_rate_stop')
            self.assertTrue(report['final_disabled_verified'])
            self.assertIsNotNone(fault_index[0])
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[fault_index[0]:]))

    def test_either_wheel_reaching_reverse_target_ends_preparation_early(self):
        for sign in (-1.,1.):
            for fast in (0,1):
                c=SelfRightingController();c(pose(.01,88.*sign),{0:0.,1:0.},LIFT_PLAN)
                speeds={0:0.,1:0.};speeds[fast]=-sign*LIFT_PLAN['pre_roll_target_rad_s']
                a=pose(.02,88.*sign);c(a,speeds,LIFT_PLAN)
                self.assertEqual(c.phase,'RISING')
                self.assertEqual(a['self_righting']['pre_roll_exit'],'speed_target')
                self.assertEqual(a['self_righting']['rise_elapsed_s'],0.)
        for target in (-1.,LIFT_PLAN['pre_roll_speed_limit_rad_s'],float('nan')):
            with self.assertRaises(Fault):
                SelfRightingController().validate_arm(pose(.01),{0:0.,1:0.},dict(LIFT_PLAN,pre_roll_target_rad_s=target))

    def test_rise_rate_window_does_not_widen_preparation_or_balance(self):
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},LIFT_PLAN)
        with self.assertRaisesRegex(Fault,'body_rotation_rate_stop'):
            c(pose(.02,rate=201.),{0:0.,1:0.},LIFT_PLAN)
        plan=dict(LIFT_PLAN,pre_roll_duration_s=0.)
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},plan)
        a=pose(.02,87.,rate=-300.);c(a,{0:0.,1:0.},plan)
        self.assertEqual(a['self_righting']['applied_pitch_rate_limit_dps'],400.)
        with self.assertRaisesRegex(Fault,'body_rotation_rate_stop'):
            c(pose(.03,86.,rate=-401.),{0:0.,1:0.},plan)
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},plan)
        c(pose(.02,7.),{0:0.,1:0.},plan)
        self.assertEqual(c.phase,'CAPTURE')
        with self.assertRaisesRegex(Fault,'body_rotation_rate_stop'):
            c(pose(.03,7.,rate=201.),{0:0.,1:0.},plan)
        for limit in (199.,401.,float('nan')):
            with self.assertRaises(Fault):
                SelfRightingController().validate_arm(pose(.01),{0:0.,1:0.},dict(plan,rise_pitch_rate_limit_dps=limit))

    def test_wider_wheel_window_is_only_rising_and_feedback_has_same_limit(self):
        plan=dict(LIFT_PLAN,pre_roll_duration_s=0.)
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},plan)
        c(pose(.02,87.),{0:13.,1:13.},plan)
        self.assertEqual(c.motor_plan(plan)['wheel_speed_limit_rad_s'],LIFT_PLAN['rise_wheel_speed_limit_rad_s'])
        row=dict(mode=1,errors_raw=0,warning_raw=0,timeout_active=False,
                 speed_rad_s=13.,torque_estimate_nm=0.,voltage_v=11.5,
                 temperature_c=40,position_rad=0.)
        health(row,1,plan=c.motor_plan(plan))
        with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
            health(dict(row,speed_rad_s=LIFT_PLAN['rise_wheel_speed_limit_rad_s']+.01),1,plan=c.motor_plan(plan))
        c(pose(.03,7.),{0:0.,1:0.},plan)
        self.assertEqual(c.phase,'CAPTURE')
        self.assertEqual(c.motor_plan(plan)['wheel_speed_limit_rad_s'],12.)
        with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
            health(row,1,plan=c.motor_plan(plan))
        for limit in (11.9,15.51,float('nan')):
            with self.assertRaises(Fault):
                SelfRightingController().validate_arm(pose(.01),{0:0.,1:0.},dict(plan,rise_wheel_speed_limit_rad_s=limit))

    def test_runner_uses_rising_feedback_window_and_stops_both_over_it(self):
        for speed,expected in ((LIFT_PLAN['rise_wheel_speed_limit_rad_s']-.5,'PASS'),(LIFT_PLAN['rise_wheel_speed_limit_rad_s']+.1,'FAIL')):
            bus=Bus(timeout=True);report={};c=SelfRightingController();injected=[]
            def exchange(mid):
                original=bus.exchange(mid)
                def wrapped(packet,phase):
                    row=original(packet,phase)
                    if mid==1 and phase=='self_righting' and c.phase=='RISING' and not injected:
                        row['speed_rad_s']=speed;injected.append(len(bus.log))
                    return row
                return wrapped
            run({m:exchange(m) for m in (0,1)},TraceIMU(bus),CAL,report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=LIFT_PLAN,
                controller=c,travel_factory=HoldTravel)
            self.assertTrue(injected)
            self.assertEqual(report['status'],expected,report.get('reason'))
            self.assertTrue(report['final_disabled_verified'])
            if expected=='FAIL':
                self.assertEqual(report['reason'],'wheel_speed_stop')
                self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[injected[0]:]))

    def test_preparation_rise_and_balance_damping_use_the_declared_phase(self):
        c=SelfRightingController();c(pose(.01),{0:0.,1:0.},LIFT_PLAN)
        self.assertEqual(c.motor_plan(LIFT_PLAN)['native_wheel_damping_nm_per_rad_s'],.03)
        c(pose(.02),{0:-8.,1:-8.},LIFT_PLAN)
        self.assertEqual(c.phase,'RISING')
        self.assertEqual(c.motor_plan(LIFT_PLAN)['native_wheel_damping_nm_per_rad_s'],LIFT_PLAN['rise_native_wheel_damping_nm_per_rad_s'])
        c(pose(.03,7.),{0:0.,1:0.},LIFT_PLAN)
        for i in range(1,70):c(pose(.03+i*.01,0.),{0:0.,1:0.},LIFT_PLAN)
        self.assertEqual(c.phase,'BALANCE')
        self.assertEqual(c.motor_plan(LIFT_PLAN)['native_wheel_damping_nm_per_rad_s'],.025)
        for value in (0.,-.01,.151,float('nan')):
            with self.assertRaises(Fault):
                SelfRightingController().validate_arm(pose(.01),{0:0.,1:0.},dict(LIFT_PLAN,pre_roll_native_wheel_damping_nm_per_rad_s=value))

    def test_rising_feedforward_headroom_keeps_net_packet_envelope(self):
        # Isolate actuator budgeting; the separate speed governor intentionally
        # removes this high-speed drive request in the deployed candidate.
        plan={k:v for k,v in LIFT_PLAN.items() if not k.startswith('rise_speed_')}
        for sign in (-1.,1.):
            c=SelfRightingController();c(pose(.01,88.*sign),{0:0.,1:0.},plan)
            self.assertEqual(c.motor_plan(plan)['feedforward_torque_limit_nm'],.50)
            c(pose(.02,88.*sign),{0:-8.*sign,1:-8.*sign},plan)
            for i in range(1,20):
                a=pose(.02+i*.01,60.*sign);speeds={0:13.*sign,1:13.*sign}
                out=c(a,speeds,plan)
                for mid in (0,1):
                    ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(mid,out[mid],c.motor_plan(plan)),4)
                    actual=ff/256000*RATIO
                    self.assertLessEqual(abs(actual),.60)
                    self.assertLessEqual(abs(actual-kd/128000000*RATIO**2*speeds[mid]),.35)
            self.assertGreater(abs(out[0]),.50)
            c(pose(.22,7.*sign),{0:0.,1:0.},plan)
            self.assertEqual(c.phase,'CAPTURE')
            self.assertEqual(c.motor_plan(plan)['feedforward_torque_limit_nm'],.50)
        for limit in (.49,.601,float('nan')):
            with self.assertRaises(Fault):
                SelfRightingController().validate_arm(pose(.01),{0:0.,1:0.},dict(LIFT_PLAN,rise_feedforward_torque_limit_nm=limit))


if __name__=='__main__':unittest.main()
