import copy
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from controller import Controller, PLAN, BASE
from engine import run
from remote_drive_keys import Keys
from two_deck_remote_drive import RemoteTravel
from test_attitude_air import CAL
from test_wheel_check import Bus
from support import begin_session, finish_session, serializable
import main


class Cue:
    def check(self): pass
    def tick(self): pass
    def deactivate(self): pass


class RuntimeTests(unittest.TestCase):
    def test_runtime_manifest_matches_reviewed_files(self):
        root=Path(__file__).resolve().parents[1]
        main.verify_tree(root,json.loads((root/'manifest.json').read_text()))

    def fixture(self, *, pose=lambda t:0., held=lambda t:False, fail=None,
                end=5., gap=False, temperature=40, waiting_faults=(), imu_gaps=(), require_reposition=False, reposition_preconfirmed=False, ack=False,
                timeout_phase=None, timeout_health_error=False, timeout_stuck=False, torque_stop_at=None, stop_motion_s=0.):
        bus=Bus(fail=fail, temp=temperature)
        keys=Keys()
        c=Controller(keys, now=bus.now)
        report={}
        armed_at=[]
        waiting_faults=list(waiting_faults)
        imu_gaps=list(imu_gaps)
        timeout_cleared=set()
        stop_started=[None]
        class IMU:
            def sample(self):
                bus.sleep(.005)
                if imu_gaps and bus.t>=imu_gaps[0]:
                    imu_gaps.pop(0)
                    bus.sleep(.031)
                if bus.t >= end:
                    raise KeyboardInterrupt('signal_15')
                keys.attach(bus.t, {103} if held(bus.t) else set())
                keys.publish(bus.t)
                a=math.radians(pose(bus.t))
                return dict(t_read_complete=bus.t, accel_g=[math.sin(a),0,math.cos(a)], gyro_dps=[0,0,0])
            def sample_nowait(self):
                a=math.radians(pose(bus.t))
                return dict(t_read_complete=bus.t, accel_g=[math.sin(a),0,math.cos(a)], gyro_dps=[0,0,0])
        def exchange(mid):
            original=bus.exchange(mid)
            def call(packet,phase):
                if phase=='arm_zero_transition': armed_at.append(bus.t)
                row=original(packet,phase)
                if phase=='stop_transition' and stop_started[0] is None:stop_started[0]=bus.t
                if phase.startswith('stop') or phase=='disabled_settling':
                    if stop_started[0] is not None and bus.t-stop_started[0]<stop_motion_s:
                        row['speed_rad_s']=.25
                if torque_stop_at is not None and phase==PLAN['control_phase'] and bus.t>=torque_stop_at:
                    row['torque_estimate_nm']=.151
                if phase=='manual_timeout_clear':timeout_cleared.add(mid)
                if timeout_stuck and phase=='timeout_clear_verify':row['timeout_active']=True
                if phase==timeout_phase and mid not in timeout_cleared:
                    row['timeout_active']=True
                    if timeout_health_error:row['errors_raw']=1
                if phase=='wait_upright_disabled' and mid==1 and waiting_faults and bus.t>=waiting_faults[0]:
                    from attitude import Fault
                    waiting_faults.pop(0)
                    raise Fault('servo_feedback_deadline_8ms')
                if gap and phase==PLAN['control_phase']:
                    bus.sleep(.03)
                row['feedback_received_monotonic']=bus.now()
                return row
            return call
        run({m:exchange(m) for m in (0,1)},IMU(),copy.deepcopy(CAL),report,ack,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=PLAN,controller=c,
            travel_factory=lambda rows,signs,p:RemoteTravel(rows,signs,p,c),
            indicator=Cue(),continuous=True,require_reposition=require_reposition,reposition_preconfirmed=reposition_preconfirmed)
        return bus,report,armed_at

    def test_waits_longer_than_old_thirty_second_trial_limit(self):
        b,r,armed=self.fixture(pose=lambda t:20. if t<31 else 0.,end=37.)
        self.assertTrue(armed, r.get('reason'))
        self.assertGreater(armed[0],32.5)
        self.assertTrue(r['final_disabled_verified'])
        self.assertLessEqual(len(r['waiting_samples']),100)

    def test_dwell_reset_when_pose_leaves_window(self):
        b,r,armed=self.fixture(pose=lambda t:20. if .8<t<1.3 else 0.)
        self.assertTrue(armed,r.get('reason'))
        self.assertGreater(armed[0],2.8)
        self.assertEqual(r['reason'],'signal_15')

    def test_held_keys_prevent_start_and_require_new_full_dwell(self):
        b,r,armed=self.fixture(held=lambda t:t<2.)
        self.assertTrue(armed,r.get('reason'))
        self.assertGreaterEqual(armed[0],3.49)

    def test_continuous_run_ignores_trial_deadline_and_evidence_is_bounded(self):
        with patch.dict(PLAN,duration_s=.1):
            b,r,armed=self.fixture(end=6.)
        self.assertTrue(armed,r.get('reason'))
        self.assertGreater(r['elapsed_s'],3.)
        self.assertEqual(r['reason'],'signal_15')
        self.assertEqual(len(r['samples']),400)
        json.dumps(serializable(r),allow_nan=False)

    def test_bus_failure_stops_both_and_never_rearms(self):
        b,r,_=self.fixture(fail=lambda m,p,phase:m==1 and phase==PLAN['control_phase'])
        self.assertEqual(r['reason'],'injected_bus_failure')
        self.assertTrue(r['final_disabled_verified'])
        stop=next(i for i,(_,_,phase) in enumerate(b.log) if phase=='stop_transition')
        self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))

    def test_timing_and_temperature_guards_remain(self):
        for options in ({'gap':True},{'temperature':81}):
            _,r,_=self.fixture(**options)
            self.assertEqual(r['status'],'FAIL')
            self.assertIn(r['reason'],('stale_sample_or_pair_deadline','servo_temperature_stop'))
            self.assertTrue(r['final_disabled_verified'])

    def test_non_upright_never_enables(self):
        b,r,armed=self.fixture(pose=lambda _:40.)
        self.assertFalse(armed)
        self.assertEqual(b.maximum_enabled,0)
        self.assertTrue(r['final_disabled_verified'])

    def test_original_upright_pitch_window_accepts_six_degrees_after_dwell(self):
        b,r,armed=self.fixture(pose=lambda _:-6.)
        self.assertTrue(armed,r.get('reason'))
        self.assertGreaterEqual(armed[0],1.5)
        self.assertEqual(PLAN['arm_pitch_limit_deg'],BASE['arm_pitch_limit_deg'])
        self.assertTrue(r['final_disabled_verified'])

    def test_disabled_feedback_glitch_requires_new_full_dwell(self):
        b,r,armed=self.fixture(waiting_faults=[1.])
        self.assertEqual(r['waiting_recovery_count'],1)
        self.assertTrue(armed,r.get('reason'))
        self.assertGreaterEqual(armed[0],2.5)
        self.assertTrue(r['final_disabled_verified'])

    def test_disabled_imu_gap_discards_frame_and_requires_fresh_full_dwell(self):
        bus,r,armed=self.fixture(imu_gaps=[1.])
        self.assertTrue(armed,r.get('reason'))
        self.assertEqual(r['waiting_recovery_count'],1)
        self.assertEqual(r['waiting_recoveries'][0]['reason'],'imu_sample_gap')
        self.assertGreaterEqual(armed[0],r['waiting_recoveries'][0]['t']+1.5)
        self.assertGreater(r['rejected_imu_sample']['sample_interval_s'],.025)
        self.assertTrue(r['final_disabled_verified'])

    def test_persistent_disabled_imu_gaps_never_enable(self):
        bus,r,armed=self.fixture(imu_gaps=[i*.2 for i in range(1,25)],end=5.)
        self.assertFalse(armed)
        self.assertEqual(bus.maximum_enabled,0)
        self.assertGreaterEqual(r['waiting_recovery_count'],10)
        self.assertTrue(r['final_disabled_verified'])

    def test_active_imu_gap_still_stops_and_latches_without_retry(self):
        bus,r,armed=self.fixture(imu_gaps=[2.])
        self.assertTrue(armed)
        self.assertEqual(r['reason'],'imu_sample_gap')
        self.assertEqual(r['waiting_recovery_count'],0)
        self.assertTrue(r['final_disabled_verified'])
        stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[stop:]))
        with tempfile.TemporaryDirectory() as folder:
            begin_session(folder,boot_id='00000000-0000-0000-0000-000000000001')
            self.assertFalse(finish_session(folder,r))
            with self.assertRaisesRegex(RuntimeError,'fault_latched'):
                begin_session(folder,boot_id='00000000-0000-0000-0000-000000000002')

    def test_repeated_disabled_feedback_failure_latches_without_enable(self):
        b,r,armed=self.fixture(waiting_faults=[.1]*5)
        self.assertFalse(armed)
        self.assertEqual(b.maximum_enabled,0)
        self.assertEqual(r['reason'],'disabled_wait_feedback_unavailable')
        self.assertTrue(r['final_disabled_verified'])

    def test_control_gains_and_active_guards_unchanged(self):
        changed={'name','arm_stable_s','arm_pitch_limit_deg','arm_roll_limit_deg',
                 'arm_pitch_span_deg','arm_rate_limit_dps','start_on_pose','handheld_wait',
                 'live_status_window_limit','wait_upright_message','pose_ready_message','active_message'}
        self.assertEqual({k:v for k,v in BASE.items() if k not in changed},
                         {k:v for k,v in PLAN.items() if k not in changed})

    def test_remote_disarm_requires_fresh_combo_for_one_second(self):
        from attitude import Fault
        keys=Keys()
        c=Controller(keys)
        # Isolate the combo from the already covered frozen balance maths.
        with patch('controller.RemoteDriveController.__call__',return_value={0:0.,1:0.}):
            keys.attach(1.,{28,158});keys.publish(1.)
            c({'t':1.},{},PLAN)
            keys.publish(1.9)
            c({'t':1.9},{},PLAN)
            # Lost input freshness cancels the held-combo timer.
            c({'t':2.2},{},PLAN)
            keys.publish(2.3)
            c({'t':2.3},{},PLAN)
            keys.publish(3.31)
            with self.assertRaisesRegex(Fault,'operator_remote_disarm'):
                c({'t':3.31},{},PLAN)

    def test_fault_or_interrupted_process_blocks_a_new_run(self):
        with tempfile.TemporaryDirectory() as folder:
            begin_session(folder, boot_id='00000000-0000-0000-0000-000000000001')
            with self.assertRaisesRegex(RuntimeError,'fault_latched'):begin_session(folder, boot_id='00000000-0000-0000-0000-000000000001')
            finish_session(folder,dict(reason='servo_temperature_stop',final_disabled_verified=True))
            with self.assertRaisesRegex(RuntimeError,'fault_latched'):begin_session(folder, boot_id='00000000-0000-0000-0000-000000000001')

    def test_shutdown_allows_next_boot_only_after_verified_disabled(self):
        for verified in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                begin_session(folder, boot_id='00000000-0000-0000-0000-000000000001')
                clean=finish_session(folder,dict(reason='signal_15',final_disabled_verified=verified))
                self.assertEqual(clean,verified)
                self.assertEqual((Path(folder)/'latch.json').exists(),not verified)

    def test_recovered_boot_still_requires_disabled_checks_neutral_keys_and_full_dwell(self):
        with tempfile.TemporaryDirectory() as folder:
            begin_session(folder, boot_id='00000000-0000-0000-0000-000000000001')
            recovered = begin_session(folder, boot_id='00000000-0000-0000-0000-000000000002')
            self.assertTrue(recovered['recovered_interrupted_boot'])
            bus, report, armed = self.fixture(pose=lambda t:20. if t<1. else 0.,
                                              held=lambda t:t<2., end=5.)
            self.assertTrue(armed, report.get('reason'))
            self.assertGreaterEqual(armed[0], 3.49)
            first = next(i for i,(_,packet,phase) in enumerate(bus.log) if packet[2]&0x70)
            self.assertGreater(first, 0)
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[:first]))
            self.assertTrue(report['final_disabled_verified'])

    def test_already_observed_fallen_pose_still_needs_new_neutral_upright_dwell(self):
        bus,r,armed=self.fixture(require_reposition=True,reposition_preconfirmed=True,
                                held=lambda t:t<1.)
        self.assertTrue(armed,r.get('reason'))
        self.assertGreaterEqual(armed[0],2.49)
        self.assertTrue(r['final_disabled_verified'])

    def test_reposition_required_does_not_rearm_if_car_stays_upright(self):
        bus,r,armed=self.fixture(require_reposition=True)
        self.assertFalse(armed)
        self.assertEqual(bus.maximum_enabled,0)
        self.assertFalse(r['reposition_seen'])

    def test_reposition_then_upright_requires_release_and_full_new_dwell(self):
        bus,r,armed=self.fixture(require_reposition=True,
            pose=lambda t:30. if t<.6 else 0.,held=lambda t:t<1.)
        self.assertTrue(armed,r.get('reason'))
        self.assertTrue(r['reposition_seen'])
        self.assertGreaterEqual(armed[0],2.49)
        self.assertTrue(r['final_disabled_verified'])

    def test_real_motion_stop_then_second_stand_in_same_supervisor(self):
        from fall_recovery import run_stand_cycles
        calls=[];saved=[]
        def attempt(report, *, require_reposition):
            calls.append(require_reposition)
            if len(calls)==1:
                bus,result,armed=self.fixture(pose=lambda t:40. if t>=2. else 0.)
                self.assertEqual(result['reason'],'body_tilt_stop')
            else:
                self.assertNotIn('samples',report)
                bus,result,armed=self.fixture(require_reposition=require_reposition,
                    pose=lambda t:30. if t<.6 else 0., held=lambda t:t<1.)
                self.assertTrue(armed,result.get('reason'))
                self.assertGreaterEqual(armed[0],2.49)
            report.update(result)
        def save(report):
            saved.append(report['reason']);return 'motion-stops/test.json'
        result=run_stand_cycles({},attempt,save,PLAN)
        self.assertEqual(calls,[False,True])
        self.assertEqual(saved,['body_tilt_stop'])
        self.assertEqual(result['stand_cycle'],1)
        self.assertEqual(result['reason'],'signal_15')
        self.assertTrue(result['final_disabled_verified'])

    def test_authorized_idle_timeout_is_cleared_only_before_new_upright_dwell(self):
        bus,r,armed=self.fixture(ack=True,timeout_phase='initial_disabled',
            require_reposition=True,reposition_preconfirmed=True,held=lambda t:t<1.)
        self.assertEqual(r['timeout_cleared_ids'],[0,1])
        self.assertTrue(armed,r.get('reason'))
        self.assertGreaterEqual(armed[0],2.49)
        clear_times=[t for t,_,phase in bus.log if phase=='manual_timeout_clear']
        self.assertTrue(clear_times and max(clear_times)<armed[0])
        self.assertEqual(r['reason'],'signal_15')

    def test_idle_timeout_ack_must_be_verified_before_any_enable(self):
        bus,r,armed=self.fixture(ack=True,timeout_phase='initial_disabled',timeout_stuck=True)
        self.assertEqual(r['reason'],'servo_timeout_no_automatic_rearm')
        self.assertFalse(armed)
        self.assertEqual(bus.maximum_enabled,0)
        self.assertTrue(r['final_disabled_verified'])

    def test_idle_timeout_without_handoff_authorization_is_not_cleared(self):
        bus,r,armed=self.fixture(timeout_phase='initial_disabled')
        self.assertEqual(r['reason'],'initial_timeout_needs_explicit_ack')
        self.assertFalse(armed)
        self.assertFalse(any(phase=='manual_timeout_clear' for _,_,phase in bus.log))

    def test_idle_timeout_with_motor_error_cannot_be_acknowledged(self):
        bus,r,armed=self.fixture(ack=True,timeout_phase='initial_disabled',timeout_health_error=True)
        self.assertEqual(r['reason'],'servo_mode_error_or_warning')
        self.assertFalse(armed)
        self.assertFalse(any(phase=='manual_timeout_clear' for _,_,phase in bus.log))

    def test_timeout_during_wait_arm_or_active_never_gets_automatic_ack(self):
        for phase in ('wait_upright_disabled','arm_zero_confirm',PLAN['control_phase']):
            bus,r,armed=self.fixture(ack=True,timeout_phase=phase)
            self.assertEqual(r['reason'],'servo_timeout_no_automatic_rearm',phase)
            self.assertFalse(any(p=='manual_timeout_clear' for _,_,p in bus.log),phase)
            self.assertTrue(r['final_disabled_verified'])

    def test_tipping_torque_stop_can_wait_for_hand_motion_then_recover(self):
        from fall_recovery import recoverable_motion_stop
        bus,r,armed=self.fixture(pose=lambda t:20. if t>=2. else 0.,
                                torque_stop_at=3.,stop_motion_s=1.6,end=7.)
        self.assertEqual(r['reason'],'estimated_torque_stop')
        self.assertTrue(r['initial_stop_confirmation']['stop_errors'])
        self.assertTrue(r['disabled_mode_confirmed_while_moving'])
        self.assertGreater(r['disabled_settling_s'],.5)
        self.assertTrue(r['final_disabled_verified'])
        self.assertTrue(recoverable_motion_stop(r,PLAN))
        stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
        self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[stop:]))

    def test_default_has_no_hardware_or_config_access(self):
        with (patch.object(main,'execute',side_effect=AssertionError('hardware')),
             patch.object(main,'load_config',side_effect=AssertionError('config')),
             redirect_stdout(io.StringIO())):
            self.assertEqual(main.main([]),0)


if __name__=='__main__':unittest.main()
