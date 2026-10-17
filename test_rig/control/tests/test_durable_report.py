import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from durable_report import persist_report
from analysis_tools.capture_trial_console import capture_stream


class DurableEvidenceTests(unittest.TestCase):
    def test_receipt_matches_full_report_after_both_syncs(self):
        report=dict(status='FAIL',reason='wheel_rolling_path_stop',
                    final_disabled_verified=True,samples=[dict(pitch_deg=.25)])
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trial.json';real_sync=os.fsync;calls=[]
            def sync(fd):calls.append(os.fstat(fd).st_mode);return real_sync(fd)
            with path.open('x') as output,patch('durable_report.os.fsync',side_effect=sync):
                receipt=persist_report(report,output)
            raw=path.read_bytes()
            self.assertEqual(json.loads(raw),report)
            self.assertEqual(receipt['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertEqual(receipt['bytes'],len(raw))
            self.assertEqual(len(calls),2)

    def test_file_or_directory_sync_failure_never_returns_success_receipt(self):
        for failures in ([OSError('file sync failed')],[None,OSError('directory sync failed')]):
            with tempfile.TemporaryDirectory() as d, (Path(d)/'r.json').open('x') as output:
                with patch('durable_report.os.fsync',side_effect=failures):
                    with self.assertRaises(OSError):persist_report({'status':'PASS'},output)

    def test_console_does_not_interpret_eof_as_success_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'console.jsonl';echo=io.StringIO()
            self.assertEqual(capture_stream(iter(['ACTIVE\n','status unknown\n']),path,echo),2)
            records=[json.loads(s) for s in path.read_text().splitlines()]
            self.assertEqual([x['kind'] for x in records],
                             ['CAPTURE_STARTED','CONSOLE_LINE','CONSOLE_LINE','STREAM_EOF'])
            self.assertEqual(records[-1]['remote_motion_status'],'NOT_INFERRED')
            before=path.read_bytes()
            with self.assertRaises(FileExistsError):capture_stream([],path,echo)
            self.assertEqual(path.read_bytes(),before)

    def test_console_received_line_survives_recorder_kill_without_false_end(self):
        script=Path(__file__).resolve().parents[1]/'analysis_tools/capture_trial_console.py'
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'console.jsonl'
            p=subprocess.Popen([sys.executable,'-u',str(script),'--output',str(path)],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                p.stdin.write('MOTION_RESULT partial test\n');p.stdin.flush()
                # Echo follows fsync, so this is a completion barrier, not a sleep.
                self.assertEqual(p.stdout.readline(),'MOTION_RESULT partial test\n')
                p.kill();p.wait(timeout=3)
                records=[json.loads(s) for s in path.read_text().splitlines()]
                self.assertEqual(records[-1]['text'],'MOTION_RESULT partial test')
                self.assertNotIn('STREAM_EOF',[x['kind'] for x in records])
            finally:
                if p.poll() is None:p.kill();p.wait(timeout=3)
                for pipe in (p.stdin,p.stdout,p.stderr):pipe.close()


if __name__=='__main__':unittest.main()
