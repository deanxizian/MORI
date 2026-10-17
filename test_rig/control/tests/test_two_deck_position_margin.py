from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from attitude import Fault
from test_two_deck_heading import frame
from two_deck_position_hold import PositionHoldController,PLAN as OLD
from two_deck_position_margin import PLAN,main


class PositionMarginTests(unittest.TestCase):
    def test_default_inert_and_only_declared_margin_changes(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertEqual({k for k in OLD if OLD[k]!=PLAN[k]},
                         {'name','active_message','wheel_speed_limit_rad_s'})

    def test_added_speed_window_keeps_net_budget_and_new_stop(self):
        for speed in (-5.9,5.9):
            c=PositionHoldController();a=frame(.005,{0:0.,1:0.})
            c(a,{0:speed,1:speed},PLAN)
            for allocation in c.allocations.values():
                self.assertLessEqual(abs(allocation.feedforward_nm),.12+1e-12)
                self.assertLessEqual(abs(allocation.predicted_net_nm),.12+1e-12)
        with self.assertRaisesRegex(Fault,'wheel_speed_stop'):
            PositionHoldController()(frame(.005,{0:0.,1:0.}),{0:6.01,1:0.},PLAN)


if __name__=='__main__':unittest.main()
