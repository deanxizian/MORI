import unittest
import tempfile
from stop_runtime import stop_for_runtime
from controller import PLAN
from test_wheel_check import Bus
from test_fall_recovery import stopped_report
from fall_recovery import motion_stop_candidate, recoverable_motion_stop
from support import begin_session, finish_session
from test_boot_recovery import BOOT_A, BOOT_B


class StopRuntimeTests(unittest.TestCase):
    def transitional_feedback(self, *, bad_phase=None, bad_field=None, bad_value=None,
                              report=None, prior_torque=None):
        bus=Bus();report=stopped_report() if report is None else report;injected=[]
        def exchange(mid):
            original=bus.exchange(mid)
            def call(packet,phase):
                self.assertEqual(packet[2]&0x70,0)
                row=original(packet,phase)
                # Recorded S288 feedback still reports the pre-command mode
                # for the first disabled exchange, then confirms mode 0.
                if phase=='stop_transition':
                    row['mode']=1
                    if prior_torque is not None:row['torque_estimate_nm']=prior_torque[mid]
                if phase==bad_phase and mid==0 and not injected:
                    injected.append(True);row[bad_field]=bad_value
                return row
            return call
        stop_for_runtime({m:exchange(m) for m in (0,1)},report,PLAN,bus.now,bus.sleep)
        return report

    def test_prior_mode_in_first_disable_reply_is_not_a_stop_fault(self):
        r=self.transitional_feedback()
        self.assertTrue(r['final_disabled_verified'])
        self.assertFalse(r.get('stop_fault_count'))
        self.assertTrue(recoverable_motion_stop(r,PLAN))
        self.assertTrue(all(row['mode']==0 for row in r['final_rows'].values()))

    def test_transition_health_faults_and_later_mode_one_remain_latched(self):
        cases=[('stop_transition','temperature_c',81),('stop_transition','errors_raw',1),
               ('stop_transition','timeout_active',True),('stop_transition','mode',2),
               ('stop_confirm','mode',1)]
        for phase,field,value in cases:
            with self.subTest(phase=phase,field=field):
                r=self.transitional_feedback(bad_phase=phase,bad_field=field,bad_value=value)
                self.assertTrue(r['final_disabled_verified'])
                self.assertTrue(r.get('stop_fault_count'))
                self.assertFalse(recoverable_motion_stop(r,PLAN))

    def test_recorded_tipping_torque_can_remain_in_first_reply_until_disable_confirmed(self):
        r=stopped_report('estimated_torque_stop')
        row=dict(r['final_rows'][0],mode=1,torque_estimate_nm=.151)
        r['samples']=[dict(attitude=dict(pitch_deg=16.,roll_deg=0.,accel_norm_g=1.),
                           wheels={0:dict(feedback=row)})]
        # First stop replies from the successful 0.1.10 recovery: both mode 1,
        # then mode 0. These are pending motion, not disabled-health samples.
        r=self.transitional_feedback(report=r,prior_torque=(.12164930555555556,-.15206163194444447))
        self.assertTrue(r['final_disabled_verified'])
        self.assertFalse(r.get('stop_fault_count'))
        self.assertEqual(len(r['pending_motion_at_disable']),2)
        self.assertTrue(recoverable_motion_stop(r,PLAN))

    def test_pending_motion_never_hides_nonmotion_health_or_confirmation_fault(self):
        for phase,field,value in [('stop_transition','temperature_c',81),
                                  ('stop_transition','voltage_v',6),
                                  ('stop_transition','errors_raw',1),
                                  ('stop_transition','timeout_active',True),
                                  ('stop_transition','torque_estimate_nm',float('nan')),
                                  ('stop_confirm','torque_estimate_nm',.152)]:
            with self.subTest(phase=phase,field=field):
                r=self.transitional_feedback(prior_torque=(.152,-.152),
                    bad_phase=phase,bad_field=field,bad_value=value)
                self.assertTrue(r['final_disabled_verified'])
                self.assertTrue(r.get('stop_fault_count'))
                self.assertFalse(recoverable_motion_stop(r,PLAN))
        r=self.transitional_feedback(report=stopped_report('late_servo_feedback'),prior_torque=(.152,-.152))
        self.assertTrue(r.get('stop_fault_count'))
        self.assertFalse(recoverable_motion_stop(r,PLAN))

    def confirmation_fault(self, fault, *, moving=False, phase='stop_confirm', mid=0):
        bus=Bus();report=stopped_report();injected=[]
        def exchange(m):
            original=bus.exchange(m)
            def call(packet,where):
                self.assertEqual(packet[2]&0x70,0)
                row=original(packet,where)
                if moving and bus.t<1.6:row['speed_rad_s']=.25
                if where==phase and m==mid and not injected:
                    injected.append(True)
                    if fault=='communication':raise TimeoutError('servo_feedback_deadline_8ms')
                    if fault=='temperature':row['temperature_c']=81
                    if fault=='warning':row['warning_raw']=1
                return row
            return call
        stop_for_runtime({m:exchange(m) for m in (0,1)},report,PLAN,bus.now,bus.sleep)
        self.assertTrue(injected)
        return report

    def test_transient_stop_fault_blocks_rearm_even_after_healthy_stationary_replies(self):
        for phase in ('stop_transition','stop_confirm'):
            for mid in (0,1):
                for fault in ('communication','temperature','warning'):
                    with self.subTest(phase=phase,mid=mid,fault=fault):
                        r=self.confirmation_fault(fault,phase=phase,mid=mid)
                        self.assertTrue(r['final_disabled_verified'])
                        self.assertFalse(recoverable_motion_stop(r,PLAN))
                        self.assertEqual(r['stop_fault_count'],1)
                        self.assertEqual(r['first_stop_fault']['phase'],phase)
                        self.assertEqual(r['stop_faults'][-1]['id'],mid)

    def test_transient_fault_blocks_extended_settling_despite_later_healthy_mode_zero(self):
        for fault in ('communication','temperature'):
            with self.subTest(fault=fault):
                r=self.confirmation_fault(fault,moving=True)
                self.assertFalse(r['final_disabled_verified'])
                self.assertNotIn('disabled_mode_confirmed_while_moving',r)
                self.assertFalse(recoverable_motion_stop(r,PLAN))

    def test_stop_fault_during_requested_shutdown_remains_latched_across_boot(self):
        r=self.confirmation_fault('temperature')
        r['reason']='signal_15'
        with tempfile.TemporaryDirectory() as folder:
            begin_session(folder,boot_id=BOOT_A)
            self.assertFalse(finish_session(folder,r))
            with self.assertRaisesRegex(RuntimeError,'fault_latched'):
                begin_session(folder,boot_id=BOOT_B)

    def exercise(self, *, mode_fault=False, error=False, failure=False, reason='wheel_speed_stop'):
        bus=Bus();report=stopped_report(reason);seen=[]
        def exchange(mid):
            original=bus.exchange(mid)
            def call(packet,phase):
                self.assertEqual(packet[2]&0x70,0)
                if failure and phase=='disabled_settling':raise RuntimeError('lost bus')
                row=original(packet,phase)
                if bus.t<1.6:row['speed_rad_s']=.25
                if mode_fault:row['mode']=1
                if error:row['errors_raw']=1
                return row
            return call
        stop_for_runtime({m:exchange(m) for m in (0,1)},report,PLAN,bus.now,bus.sleep,
                         status=lambda rows:seen.append(bus.t))
        return bus,report,seen

    def test_mode_zero_movement_waits_without_enable_until_three_still_pairs(self):
        bus,r,seen=self.exercise()
        self.assertTrue(r['final_disabled_verified'])
        self.assertGreaterEqual(bus.t,1.64-1e-9)
        self.assertTrue(seen)
        self.assertTrue(r['disabled_mode_confirmed_while_moving'])
        self.assertFalse(r['physical_power_cut_required'])
        self.assertTrue(r['initial_stop_confirmation']['stop_errors'])

    def test_unconfirmed_disable_or_motor_error_does_not_enter_wait(self):
        for options in ({'mode_fault':True},{'error':True}):
            bus,r,seen=self.exercise(**options)
            self.assertFalse(r['final_disabled_verified'])
            self.assertFalse(seen)
            self.assertLess(bus.t,1.1)

    def test_communication_failure_during_settling_blocks_recovery(self):
        bus,r,seen=self.exercise(failure=True)
        self.assertEqual(r['reason'],'lost bus')
        self.assertEqual(r['motion_stop_before_settling_fault'],'wheel_speed_stop')
        self.assertTrue(seen)

    def test_nonmotion_fault_does_not_gain_indefinite_wait(self):
        bus,r,seen=self.exercise(reason='late_servo_feedback')
        self.assertFalse(seen)
        self.assertFalse(r['final_disabled_verified'])

    def test_only_tilt_associated_transient_torque_is_candidate(self):
        r=stopped_report('estimated_torque_stop')
        row=dict(r['final_rows'][0],mode=1,torque_estimate_nm=.151)
        r['samples']=[dict(attitude=dict(pitch_deg=16.,roll_deg=0.,accel_norm_g=1.),
                           wheels={0:dict(feedback=row)})]
        self.assertTrue(motion_stop_candidate(r,PLAN))
        r['samples'][0]['attitude']['pitch_deg']=0.
        self.assertFalse(motion_stop_candidate(r,PLAN))
        r['samples'][0]['attitude']['pitch_deg']=16.
        r['reason']='estimated_torque_sustained_stop'
        self.assertFalse(motion_stop_candidate(r,PLAN))
        r['reason']='estimated_torque_stop';row['errors_raw']=1
        self.assertFalse(motion_stop_candidate(r,PLAN))
