import io
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from self_righting_morning_supply import PLAN,main
from self_righting_headroom_window import PLAN as HELD


class MorningSupplyTests(unittest.TestCase):
    def test_default_has_no_file_or_motor_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_incomplete_start_flags_cannot_open_hardware(self):
        with patch('air_trial.sys.platform','linux'), \
             patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            main(['--run-morning-supply'])

    def test_executed_profile_preserved_and_overnight_entry_stays_held(self):
        metadata={'name','active_message','motion_hold_reason'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in metadata},
                         {k:v for k,v in HELD.items() if k not in metadata})
        self.assertTrue(PLAN['motion_hold_reason'])
        self.assertTrue(HELD['motion_hold_reason'])


if __name__=='__main__':unittest.main()
