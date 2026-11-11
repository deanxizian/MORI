import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from support import begin_session, finish_session

BOOT_A = '00000000-0000-0000-0000-000000000001'
BOOT_B = '00000000-0000-0000-0000-000000000002'


class BootRecoveryTests(unittest.TestCase):
    def test_interrupted_new_boot_archives_exact_bytes_and_starts_fresh(self):
        with tempfile.TemporaryDirectory() as folder:
            first = begin_session(folder, boot_id=BOOT_A)
            self.assertFalse(first['recovered_interrupted_boot'])
            marker = Path(folder)/'latch.json'
            old = marker.read_bytes()
            second = begin_session(folder, boot_id=BOOT_B)
            self.assertTrue(second['recovered_interrupted_boot'])
            self.assertEqual((Path(folder)/second['previous_session_archive']).read_bytes(), old)
            self.assertEqual(json.loads(marker.read_text())['boot_id'], BOOT_B)
            # This admitted run cannot be re-entered after a same-boot crash.
            with self.assertRaisesRegex(RuntimeError, 'fault_latched'):
                begin_session(folder, boot_id=BOOT_B)

    def test_known_fault_remote_disarm_and_unverified_stop_survive_power_cycle(self):
        for reason in ('servo_temperature_stop','wheel_speed_stop','late_servo_feedback',
                       'operator_remote_disarm','signal_15'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder:
                begin_session(folder, boot_id=BOOT_A)
                finish_session(folder, dict(reason=reason, final_disabled_verified=reason!='signal_15'))
                old = (Path(folder)/'latch.json').read_bytes()
                with self.assertRaisesRegex(RuntimeError, 'fault_latched'):
                    begin_session(folder, boot_id=BOOT_B)
                self.assertEqual((Path(folder)/'latch.json').read_bytes(), old)

    def test_unknown_legacy_corrupt_or_fault_marker_never_auto_recovers(self):
        markers = [b'broken', b'null', b'[]',
                   json.dumps(dict(state='RUNNING_OR_INTERRUPTED')).encode(),
                   json.dumps(dict(state='RUNNING_OR_INTERRUPTED', schema_version=2, boot_id='bad')).encode(),
                   json.dumps(dict(state='FAULT_LATCHED', schema_version=2, boot_id=BOOT_A)).encode()]
        for raw in markers:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as folder:
                marker = Path(folder)/'latch.json';marker.write_bytes(raw)
                with self.assertRaisesRegex(RuntimeError, 'fault_latched'):
                    begin_session(folder, boot_id=BOOT_B)
                self.assertEqual(marker.read_bytes(), raw)

    def test_kernel_identity_not_wall_clock_controls_admission(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('support.current_boot_id', return_value=BOOT_A), patch('support.time.time',return_value=200.):
                begin_session(folder)
            with patch('support.current_boot_id', return_value=BOOT_A), patch('support.time.time',return_value=999999.):
                with self.assertRaisesRegex(RuntimeError,'fault_latched'):begin_session(folder)
            with patch('support.current_boot_id', return_value=BOOT_B), patch('support.time.time',return_value=0.):
                self.assertTrue(begin_session(folder)['recovered_interrupted_boot'])

    def test_clean_shutdown_starts_without_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            begin_session(folder, boot_id=BOOT_A)
            self.assertTrue(finish_session(folder,dict(reason='signal_15', final_disabled_verified=True)))
            self.assertFalse(begin_session(folder, boot_id=BOOT_B)['recovered_interrupted_boot'])

    def test_shutdown_with_stop_or_observer_fault_never_clears_latch(self):
        findings=[{'stop_fault_count':1}, {'stop_faults':[{'error':'lost'}]},
                  {'stop_transition_findings':[{'error':'lost'}]}, {'stop_errors':{0:'lost'}},
                  {'stop_observer_findings':['bad sample']}, {'stop_observer_setup_error':'bad sensor'},
                  {'stop_imu_observation':{'status':'FAIL'}}]
        for finding in findings:
            with self.subTest(finding=finding), tempfile.TemporaryDirectory() as folder:
                begin_session(folder,boot_id=BOOT_A)
                report=dict(reason='signal_15',final_disabled_verified=True,**finding)
                self.assertFalse(finish_session(folder,report))
                with self.assertRaisesRegex(RuntimeError,'fault_latched'):
                    begin_session(folder,boot_id=BOOT_B)

    def test_failed_archive_write_leaves_previous_marker_and_aborts(self):
        with tempfile.TemporaryDirectory() as folder:
            begin_session(folder,boot_id=BOOT_A)
            marker=Path(folder)/'latch.json';old=marker.read_bytes()
            original=Path.open
            def fail_archive(p,*args,**kwargs):
                if p.name.startswith('power-interrupted-'):raise OSError('disk unavailable')
                return original(p,*args,**kwargs)
            with patch.object(Path,'open',fail_archive):
                with self.assertRaisesRegex(OSError,'disk unavailable'):
                    begin_session(folder,boot_id=BOOT_B)
            self.assertEqual(marker.read_bytes(),old)
