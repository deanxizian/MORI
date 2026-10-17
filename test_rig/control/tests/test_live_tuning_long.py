import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import LiveTuningController,TuningChannel
from live_tuning_policy import gains,validate_plan_change
from test_live_tuning import sample,checked_pair
from two_deck_live_tuning import PLAN as SHORT
from two_deck_live_tuning_long import PLAN,main


class LongLiveTests(unittest.TestCase):
    def test_only_observation_budgets_change_and_default_remains_inert(self):
        self.assertEqual({k for k in set(SHORT)|set(PLAN) if SHORT.get(k)!=PLAN.get(k)},
                         {'name','duration_s','rolling_path_limit_m','active_message'})
        self.assertEqual(SHORT['duration_s'],300.)
        self.assertEqual(PLAN['duration_s'],600.)
        self.assertEqual(PLAN['rolling_path_limit_m'],6.)
        self.assertEqual(PLAN['net_rolling_limit_m'],.30)
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        with self.assertRaises(ValueError):validate_plan_change(SHORT,dict(SHORT,duration_s=600.))
        with self.assertRaises(ValueError):validate_plan_change(SHORT,dict(SHORT,rolling_path_limit_m=6.))

    def test_long_cumulative_budget_still_stops_and_net_window_is_unchanged(self):
        def guard():return HoldTravel({0:{'position_rad':0.},1:{'position_rad':0.}}, {0:1,1:-1},PLAN)
        g=guard()
        def cycle():
            g.update(0,{'position_rad':.25});g.update(1,{'position_rad':-.25})
            g.update(0,{'position_rad':0.});g.update(1,{'position_rad':0.})
        for _ in range(110):cycle()
        self.assertGreater(g.path[0],2.);self.assertEqual(g.offset,{0:0.,1:0.})
        with self.assertRaisesRegex(Fault,'wheel_rolling_path_stop'):
            for _ in range(210):cycle()
        g=guard()
        with self.assertRaisesRegex(Fault,'wheel_net_travel_stop'):
            for i in range(1,33):
                g.update(0,{'position_rad':i*.25});g.update(1,{'position_rad':-i*.25})
        self.assertLess(g.path[0],.32)

    def test_exact_commands_equal_short_entry_and_filters_do_not_reset(self):
        a=LiveTuningController(TuningChannel(gains(PLAN)))
        b=LiveTuningController(TuningChannel(gains(SHORT)))
        for i in range(1,1201):
            x=sample(i*.005);y=copy.deepcopy(x)
            ca=a(x,{0:0.,1:0.},PLAN);cb=b(y,{0:0.,1:0.},SHORT)
            self.assertEqual(ca,cb)
            if i>1:self.assertFalse(x['ardupilot_balance']['filter_reset'])
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(a.allocated_torque_packet(mid,sign,ca[mid],PLAN),
                                 b.allocated_torque_packet(mid,sign,cb[mid],SHORT))

    def test_rejects_longer_than_authorized_and_retains_ten_minute_windows(self):
        c=LiveTuningController(TuningChannel(gains(PLAN)))
        with self.assertRaisesRegex(Fault,'invalid_live_tuning_plan'):
            c(sample(.005),{0:0.,1:0.},dict(PLAN,duration_s=600.01))
        c=LiveTuningController(TuningChannel(gains(PLAN)))
        a=sample(.005);c(a,{0:0.,1:0.},PLAN)
        # Exercise only bounded telemetry retention, not a fake physical run.
        for i in range(60):
            for t in [5.1+10.001*i,15.1+10.001*i]:
                x=copy.deepcopy(a);x['t']=t;x['live_tuning']['state']='READY'
                c.observe_pair(checked_pair(x))
        self.assertGreater(len(c.windows),32)
        self.assertLessEqual(len(c.windows),64)


if __name__=='__main__':unittest.main()
