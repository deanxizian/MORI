import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from fall_recovery import (RepositionGate, MOTION_STOPS, recoverable_motion_stop,
                           run_stand_cycles, archive_motion_stop, disabled_reposition_seen, initial_timeout_ack_allowed)
from controller import PLAN
from test_wheel_check import Bus
from protocol import locked_query


def stopped_report(reason='body_tilt_stop'):
    bus=Bus()
    return dict(reason=reason,control_cycles=30,final_disabled_verified=True,
                final_rows={m:bus.exchange(m)(locked_query(m),'stop_confirm') for m in (0,1)})


class FallRecoveryTests(unittest.TestCase):
    def test_only_motion_stops_after_confirmed_active_run_are_eligible(self):
        for reason in MOTION_STOPS:
            self.assertTrue(recoverable_motion_stop(stopped_report(reason),PLAN))
        for reason in ('imu_sample_gap','late_servo_feedback','estimated_torque_stop',
                       'servo_temperature_stop','operator_remote_disarm','signal_15',
                       'unexpected_motion_during_zero_torque_arm','acceleration_outside_test_window'):
            self.assertFalse(recoverable_motion_stop(stopped_report(reason),PLAN))
        for changes in ({'control_cycles':0},{'final_disabled_verified':False},
                        {'stop_transition_findings':['timeout']},{'stop_errors':{'0':'lost'}},
                        {'stop_observer_findings':['imu gap']},{'stop_imu_observation':{'status':'FAIL'}}):
            self.assertFalse(recoverable_motion_stop(dict(stopped_report(),**changes),PLAN))

    def test_final_motor_health_must_be_valid_on_both_wheels(self):
        for field,value in (('mode',1),('speed_rad_s',.1),('temperature_c',81),
                            ('errors_raw',1),('warning_raw',1),('timeout_active',True),
                            ('voltage_v',6),('torque_estimate_nm',.2),('speed_rad_s',float('nan'))):
            for mid in (0,1):
                r=stopped_report();r['final_rows'][mid][field]=value
                self.assertFalse(recoverable_motion_stop(r,PLAN),(mid,field))
        r=stopped_report();del r['final_rows'][1]
        self.assertFalse(recoverable_motion_stop(r,PLAN))

    def test_brief_tilt_and_interrupted_observation_do_not_count(self):
        gate=RepositionGate()
        def a(t,p):return dict(t=t,pitch_deg=p,roll_deg=0.)
        self.assertFalse(gate.update(a(0.,20.)))
        self.assertFalse(gate.update(a(.2,20.)))
        gate.interrupt()
        self.assertFalse(gate.update(a(.3,20.)))
        self.assertFalse(gate.update(a(.4,0.)))
        self.assertFalse(gate.update(a(.5,20.)))
        self.assertTrue(gate.update(a(.8,20.)))
        self.assertTrue(gate.update(a(.9,0.)))

    def test_saved_stop_failure_prevents_another_attempt(self):
        calls=[]
        def attempt(report,**kwargs):calls.append(1);report.update(stopped_report())
        def fail(_):raise OSError('disk full')
        result=run_stand_cycles({},attempt,fail,PLAN)
        self.assertEqual(calls,[1])
        self.assertEqual(result['reason'],'disk full')

    def test_unknown_second_attempt_failure_returns_current_report(self):
        calls=[]
        def attempt(report,**kwargs):
            calls.append(1)
            if len(calls)==2:raise RuntimeError('sensor unavailable')
            report.update(stopped_report())
        result=run_stand_cycles({},attempt,lambda r:'saved.json',PLAN)
        self.assertEqual(len(calls),2)
        self.assertEqual(result['stand_cycle'],1)
        self.assertEqual(result['reason'],'sensor unavailable')
        self.assertFalse(result['final_disabled_verified'])

    def test_motion_stop_archive_preserves_guard_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            report=stopped_report()
            name=archive_motion_stop(folder,report)
            archived=json.loads((Path(folder)/name).read_text())
            self.assertEqual(archived['reason'],'body_tilt_stop')
            self.assertEqual((Path(folder)/name).read_bytes(),(Path(folder)/'last-result.json').read_bytes())

    def evidence(self, dt=.005, confirmation=0.):
        a=math.radians(30.)
        return dict(stop_confirmation_complete_monotonic=confirmation,
                    stop_imu_observation=dict(status='PASS',samples=[
                        dict(imu=dict(t_read_complete=i*dt,accel_g=[math.sin(a),0.,math.cos(a)],
                                      gyro_dps=[0.,0.,0.])) for i in range(100)]))

    def test_post_stop_pose_observation_can_credit_fallen_pose(self):
        from test_attitude_air import CAL
        self.assertTrue(disabled_reposition_seen(self.evidence(),CAL,PLAN))

    def test_pose_before_verified_stop_cannot_credit_reposition(self):
        from test_attitude_air import CAL
        self.assertFalse(disabled_reposition_seen(self.evidence(confirmation=1.),CAL,PLAN))

    def test_sparse_or_failed_passive_observation_cannot_credit_reposition(self):
        from test_attitude_air import CAL
        self.assertFalse(disabled_reposition_seen(self.evidence(dt=.1),CAL,PLAN))
        r=self.evidence();r['stop_imu_observation']['status']='FAIL'
        self.assertFalse(disabled_reposition_seen(r,CAL,PLAN))

    def test_recovery_ack_requires_explicit_verified_handoff_and_saved_record(self):
        self.assertTrue(initial_timeout_ack_allowed({'stand_cycle':0}))
        base=dict(stand_cycle=1,previous_motion_stop='wheel_speed_stop',
                  disabled_idle_timeout_ack_authorized=True,previous_stop_archive='motion-stops/test.json')
        self.assertTrue(initial_timeout_ack_allowed(base))
        for key in ('previous_motion_stop','disabled_idle_timeout_ack_authorized','previous_stop_archive'):
            r=base.copy();del r[key]
            self.assertFalse(initial_timeout_ack_allowed(r))
        base['previous_motion_stop']='late_servo_feedback'
        self.assertFalse(initial_timeout_ack_allowed(base))
