import io
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch
from self_righting_charged_supply import main
from air_trial import PORT

class ChargeHoldTests(unittest.TestCase):
    def test_even_all_run_flags_cannot_open_hardware_during_charge_hold(self):
        args=['--run-charged-supply-recovery','--operator-ready','--ack-query-timeout',
              '--port',PORT,'--calibration','not-opened.json','--output','not-created.json']
        errors=io.StringIO()
        with patch('air_trial.sys.platform','linux'),patch('pathlib.Path.read_bytes',side_effect=AssertionError('I/O')),patch('air_trial.run',side_effect=AssertionError('motor I/O')),redirect_stderr(errors),self.assertRaises(SystemExit):
            main(args)
        self.assertIn('motion_trial_on_hold',errors.getvalue())

if __name__=='__main__':unittest.main()
