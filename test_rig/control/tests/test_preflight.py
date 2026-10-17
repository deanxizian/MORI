import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch,MagicMock
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('probe',ROOT/'preflight.py')
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ProbeTests(unittest.TestCase):
    def test_default_zero_hardware_io(self):
        r=subprocess.run([sys.executable,str(ROOT/'preflight.py')],check=True,capture_output=True,text=True)
        self.assertFalse(json.loads(r.stdout)['hardware_opened'])

    def test_only_disabled_packets_and_reject_active_feedback(self):
        packets=[]
        def exchange(packet,phase):
            packets.append(packet)
            return dict(mode=0,speed_rad_s=0,errors_raw=0,warning_raw=0)
        for mid in (0,1):
            probe.disabled_exchange(exchange,mid,'test')
            self.assertEqual((packets[-1][2]>>4)&7,0)
            self.assertTrue(packets[-1][2]&128)
            self.assertEqual(packets[-1][4:16],bytes(12))
        for mode,speed in ((1,0),(0,.1),(0,float('nan'))):
            def bad(*_):return dict(mode=mode,speed_rad_s=speed,errors_raw=0,warning_raw=0)
            with self.assertRaises(RuntimeError):probe.disabled_exchange(bad,0,'test')

    def test_signed_imu_scaling_and_reject_saturation(self):
        s=probe.decode([0,8192,65536-8192,3277,65536-3277,0,512])
        self.assertEqual(s['accel_g'],[0,1,-1])
        self.assertAlmostEqual(s['gyro_dps'][0],100,delta=.02)
        self.assertAlmostEqual(s['gyro_dps'][1],-100,delta=.02)
        with self.assertRaises(ValueError):probe.decode([32767,0,0,0,0,0,0])

    def test_bandwidth_selection_preserves_rate_and_ranges(self):
        a=probe.RawIMU({});b=probe.RawIMU({},bandwidth_divisor=4)
        self.assertEqual(a.requested_config,{0x20:0x4018,0x21:0x4038})
        self.assertEqual(b.requested_config,{0x20:0x4098,0x21:0x40b8})
        for reg in a.requested_config:
            self.assertEqual(a.requested_config[reg]^b.requested_config[reg],0x80)
        for invalid in (0,1,3,8,4.,True,float('nan')):
            with self.assertRaises(ValueError):probe.RawIMU({},bandwidth_divisor=invalid)

    def test_selected_filter_readback_and_restore_on_failure(self):
        for mismatch in (False,True):
            report={};s=probe.RawIMU(report,bandwidth_divisor=4)
            regs={0:0x43,1:0,0x20:0x28,0x21:0x48};saved=regs.copy()
            def read(reg,n=1):
                v=regs[reg]
                if mismatch and reg==0x20 and v==0x4098:v^=0x80
                return (v,)
            s.read=read;s.write=lambda reg,value:regs.__setitem__(reg,value)
            bus=MagicMock();module=SimpleNamespace(SMBus=lambda _:bus)
            with patch.dict(sys.modules,{'smbus2':module}),patch('builtins.open',return_value=MagicMock()),patch.object(probe.fcntl,'flock'),patch.object(probe.time,'sleep'):
                if mismatch:
                    with self.assertRaisesRegex(RuntimeError,'readback_mismatch'):s.__enter__()
                else:
                    with s:self.assertEqual(report['config_during'],{0x20:0x4098,0x21:0x40b8})
            self.assertEqual(regs,saved)
            self.assertTrue(report['configuration_restored'])
            bus.close.assert_called_once()


if __name__=='__main__':unittest.main()
