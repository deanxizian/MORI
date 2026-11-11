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
