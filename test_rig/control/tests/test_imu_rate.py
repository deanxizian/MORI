import io
import sys
import unittest
from contextlib import redirect_stdout,redirect_stderr
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
from preflight import RawIMU,main
from self_righting_capture_velocity_window import main as used_main


class IMURateTests(unittest.TestCase):
    def test_200_rate_changes_only_odr_bits_not_ranges_or_bandwidth(self):
        for bw in (2,4):
            a=RawIMU({},bandwidth_divisor=bw);b=RawIMU({},bandwidth_divisor=bw,odr_hz=200)
            self.assertEqual(b.report['odr_hz'],200)
            for reg in (0x20,0x21):self.assertEqual(a.requested_config[reg]^b.requested_config[reg],1)
        self.assertEqual(RawIMU({},bandwidth_divisor=4,odr_hz=200).requested_config,{0x20:0x4099,0x21:0x40b9})

    def test_invalid_rates_rejected_before_io(self):
        for bad in (50,400,200.,True,'200',float('nan')):
            with self.assertRaisesRegex(ValueError,'unsupported_imu_odr'):RawIMU({},odr_hz=bad)

    def test_200_readback_and_restore_on_success_or_mismatch(self):
        for mismatch in (False,True):
            report={};s=RawIMU(report,odr_hz=200,bandwidth_divisor=4)
            regs={0:0x43,1:0,0x20:0x28,0x21:0x48};saved=regs.copy()
            def read(reg,n=1):
                v=regs[reg]
                return ((v^1) if mismatch and reg==0x20 and v==0x4099 else v,)
            s.read=read;s.write=lambda reg,value:regs.__setitem__(reg,value)
            bus=MagicMock();module=SimpleNamespace(SMBus=lambda _:bus)
            with patch.dict(sys.modules,{'smbus2':module}),patch('builtins.open',return_value=MagicMock()), \
                 patch('preflight.fcntl.flock'),patch('preflight.time.sleep'):
                if mismatch:
                    with self.assertRaisesRegex(RuntimeError,'readback_mismatch'):s.__enter__()
                else:
                    with s:self.assertEqual(report['config_during'],{0x20:0x4099,0x21:0x40b9})
            self.assertEqual(regs,saved);self.assertTrue(report['configuration_restored'])
            bus.close.assert_called_once()

    def test_default_200_plan_still_has_zero_hardware_io(self):
        with patch('builtins.open',side_effect=AssertionError('file IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--hz','200','--imu-odr-hz','200']),0)

    def test_measure_rate_above_sensor_odr_rejects_before_io(self):
        with patch('builtins.open',side_effect=AssertionError('file IO')),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):main(['--measure','--hz','200','--imu-odr-hz','100'])

    def test_used_motion_entry_rejects_before_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                used_main(['--run-capture-velocity-window','--operator-ready','--ack-query-timeout',
                    '--port','unused','--calibration','unused','--output','unused'])


if __name__=='__main__':unittest.main()
