import ctypes
import importlib.util
import json
import os
import pathlib
import select
import subprocess
import tempfile
import threading
import time
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mori_cli',ROOT/'tools/mori_cli.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)

class Commands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'reports')
        lib=pathlib.Path(cls.temp.name)/'parser.dylib'
        core=ROOT/'firmware_work/firmware/components/mori_core'
        subprocess.run(['cc','-std=c11','-dynamiclib','-I'+str(core/'include'),str(core/'mori_protocol.c'),'-o',str(lib)],check=True)
        cls.lib=ctypes.CDLL(str(lib));cls.lib.mori_parse.argtypes=[ctypes.c_char_p,ctypes.c_void_p]
        cls.lib.mori_parse.restype=ctypes.c_int
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def test_valid_parity(self):
        for command in ['info','status','calibrate','arm bench','duty .12 -.12','confirm_signs','gains 1 .05 .1 0','arm balance','move .3 -.1','head -50','stop','disarm','ack']:
            with self.subTest(command=command):
                cli.validate_command(command)
                self.assertEqual(self.lib.mori_parse(command.encode(),ctypes.create_string_buffer(256)),0)
    def test_invalid_parity(self):
        for command in ['head nan','head Inf','head 1e300','head 1e-300','head 1e-40','head 51','head 0x1p0','duty .13 0','move .1 .1 extra','gains 1 0 0 0','gains 1 .1 -1 0','arm bench x','@9 stop','head','stop\narm bench']:
            with self.subTest(command=command):
                with self.assertRaises(ValueError): cli.validate_command(command)
                if not command.startswith('@'):
                    self.assertNotEqual(self.lib.mori_parse(command.encode(),ctypes.create_string_buffer(256)),0)
    def test_packet_boundary(self):
        self.assertEqual(cli.request_bytes('stop',0xffffffff),b'@4294967295 stop\n')
        for identifier in [0,-1,0x100000000]:
            with self.assertRaises(ValueError): cli.request_bytes('stop',identifier)
        for command in ['head 0\0stop','head 0\r','x'*120]:
            with self.assertRaises(ValueError):cli.validate_command(command)

class Recordings(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'reports')
        self.path=pathlib.Path(self.temp.name)/'SIMULATED_capture.csv'
    def tearDown(self): self.temp.cleanup()
    def row(self,seq=1):
        values={h:'0' for h in cli.HEADER};values.update(seq=str(seq),device_us=str(1000000+seq*2404),state='DISARMED',run_us='520',max_run_us='520')
        return ','.join(values[h] for h in cli.HEADER)
    def test_capture_replay_and_quantiles(self):
        r=cli.Recorder(self.path,'SIMULATED',1)
        r.feed('HEADER MORI/1 '+','.join(cli.HEADER))
        for seq in [1,2,4,1,2]:r.feed('DATA '+self.row(seq))
        meta=r.close();result=cli.replay(self.path)
        self.assertEqual(meta['rows'],5);self.assertEqual(result['resets_or_clock_discontinuities'],1)
        self.assertEqual(result['estimated_missing_telemetry_rows'],1)
        self.assertEqual(result['timing_sample_quantiles_us']['run_us']['p99'],520)
        self.assertEqual(meta['source'],'SIMULATED');self.assertEqual(meta['physical_validation'],'NOT_TESTED')
        self.assertEqual(meta['csv_sha256'],json.loads(self.path.with_suffix('.meta.json').read_text())['csv_sha256'])
    def test_bad_rows_preserved_but_not_accepted(self):
        r=cli.Recorder(self.path,'SIMULATED')
        r.feed('HEADER MORI/1 '+','.join(cli.HEADER));r.feed('DATA '+self.row()+',extra')
        fields=self.row().split(',');fields[cli.HEADER.index('pitch_rad')]='nan';r.feed('DATA '+','.join(fields))
        r.feed('DATA 1,2,DISARMED');r.feed('INVALID serial line overflow')
        meta=r.close();self.assertEqual(meta['invalid_rows'],4);self.assertEqual(meta['rows'],0)
        self.assertIn('nan',self.path.with_suffix('.raw.jsonl').read_text())
    def test_simulation_filename_required(self):
        with self.assertRaises(ValueError):cli.Recorder(self.path.with_name('real.csv'),'SIMULATED')
    def test_hash_change_rejected(self):
        r=cli.Recorder(self.path,'SIMULATED',1);r.feed('HEADER MORI/1 '+','.join(cli.HEADER));r.feed('DATA '+self.row());r.close()
        self.path.write_text(self.path.read_text().replace('520','521'))
        with self.assertRaises(ValueError):cli.replay(self.path)
    def test_legacy_replay(self):
        legacy=self.path.with_name('legacy.csv')
        values={h:'0' for h in cli.LEGACY_HEADER};values['state']='DISARMED'
        legacy.write_text(','.join(cli.LEGACY_HEADER)+'\n'+','.join(values[h] for h in cli.LEGACY_HEADER)+'\n')
        self.assertEqual(cli.replay(legacy)['source'],'LEGACY_UNVERIFIED')
    def test_quantile_nearest_rank(self):
        q=cli.quantiles(list(range(1,101)))
        self.assertEqual((q['p50'],q['p95'],q['p99'],q['max']),(50,95,99,100))
    def test_live_adapter_on_simulated_pty(self):
        master,slave=os.openpty();path=os.ttyname(slave)
        recorder=cli.Recorder(self.path,'SIMULATED')
        serial=cli.SerialPort(path);received=[];errors=[]
        def device():
            try:
                if not select.select([master],[],[],1)[0]:raise AssertionError('request not sent')
                data=os.read(master,1024);received.append(data)
                os.write(master,b'ACK 27 MORI/1 reason=OK state=DISARMED fault=0\n')
            except Exception as e:errors.append(e)
        thread=threading.Thread(target=device);thread.start()
        try:
            result=cli.transaction(serial,'status',27,recorder,.5)
            self.assertTrue(result['response'].startswith('ACK 27 '))
        finally:
            thread.join();serial.close();os.close(master);os.close(slave);meta=recorder.close()
        self.assertFalse(errors);self.assertEqual(received,[b'@27 status\n'])
        self.assertEqual(meta['command_rtt_us']['samples'],1)
    def test_timeout_never_retries(self):
        class Silent:
            def __init__(self):self.writes=[]
            def write(self,p):self.writes.append(p)
            def lines(self,t):time.sleep(min(t,.001));return []
        serial=Silent();r=cli.Recorder(self.path,'SIMULATED')
        try:
            with self.assertRaises(TimeoutError):cli.transaction(serial,'stop',21,r,.01)
        finally:r.close()
        self.assertEqual(serial.writes,[b'@21 stop\n'])

if __name__=='__main__':unittest.main()
