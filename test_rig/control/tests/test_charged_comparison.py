import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from self_righting_charged_compare import PLAN, main
from self_righting_inward_momentum import PLAN as REFERENCE
from self_righting_charged_supply import PLAN as HELD


class ChargedComparisonTests(unittest.TestCase):
    def test_default_remains_inert_before_file_or_motor_io(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_partial_launch_flags_cannot_open_files_or_hardware(self):
        with patch('air_trial.sys.platform','linux'), \
             patch('pathlib.Path.read_bytes',side_effect=AssertionError('file IO')), \
             patch('air_trial.run',side_effect=AssertionError('motor IO')), \
             redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            main(['--run-post-charge-comparison'])

    def test_all_control_parameters_match_reference_and_old_charge_entry_stays_held(self):
        metadata={'name','active_message','motion_hold_reason'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in metadata},
                         {k:v for k,v in REFERENCE.items() if k not in metadata})
        self.assertTrue(PLAN['motion_hold_reason'])
        self.assertTrue(HELD['motion_hold_reason'])


if __name__=='__main__':unittest.main()
