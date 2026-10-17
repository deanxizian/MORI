import time
import unittest
from unittest.mock import patch

from air_trial import display_indicator
from attitude import Fault
from cam_indicator import CamIndicator,IndicatorError
from ground_constant_rate_probe import PLAN
from test_cam_indicator import Port


class HeldDiagnosticCueTests(unittest.TestCase):
    def test_motor_diagnostic_factory_selects_off_only_default_balance_retains_red(self):
        with patch('cam_indicator.CamIndicator') as factory:
            report={};display_indicator(report,PLAN)
            factory.assert_called_once_with(report,active_red=False)
        with patch('cam_indicator.CamIndicator') as factory:
            report={};display_indicator(report,{})
            factory.assert_called_once_with(report,active_red=True)
        for value in ('false',0,1,None):
            with self.assertRaises(Fault):display_indicator({},dict(PLAN,operator_held_diagnostic=value))

    def test_active_held_diagnostic_never_sends_red_or_balance_tone(self):
        port=Port();report={}
        with CamIndicator(report,port=port,active_red=False) as cue:
            end=time.monotonic()+.2
            while time.monotonic()<end:
                cue.tick();time.sleep(.01)
            self.assertFalse(cue.ack_visible)
            self.assertIsNotNone(cue.active_since)
        self.assertNotIn(b'M',port.writes)
        self.assertNotIn(b'b',port.writes)
        self.assertTrue(report['final_off_frame_acknowledged'])
        self.assertEqual(report['cue_semantics'],'operator_held_diagnostic_red_off')
        self.assertIn('held_diagnostic_active',[x['event'] for x in report['events']])
        self.assertNotIn('compensation_active',[x['event'] for x in report['events']])

    def test_controller_expiry_still_faults_and_red_stays_off(self):
        port=Port();report={}
        with CamIndicator(report,port=port,active_red=False) as cue:
            cue.tick();time.sleep(.23)
            with self.assertRaisesRegex(IndicatorError,'control_heartbeat_expired'):cue.check()
        self.assertNotIn(b'M',port.writes)
        self.assertNotIn(b'b',port.writes)

    def test_missing_off_ack_or_wrong_visible_frame_is_not_accepted(self):
        port=Port()
        with CamIndicator({},port=port,active_red=False) as cue:
            port.silent=True
            with self.assertRaisesRegex(IndicatorError,'ack_stale'):
                end=time.monotonic()+1.
                while time.monotonic()<end:
                    cue.tick();time.sleep(.01)
        clock=[10.];port=Port();cue=CamIndicator({},port=port,now=lambda:clock[0],active_red=False)
        cue._line(b'MORI_MOTION_ACK 10 0');cue.tick()
        cue._line(b'MORI_MOTION_ACK 11 1');cue._sound_tick()
        with self.assertRaisesRegex(IndicatorError,'unexpected_red'):cue.check()
        self.assertNotIn(b'b',port.writes)


if __name__=='__main__':unittest.main()
