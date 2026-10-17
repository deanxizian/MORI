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
from two_deck_live_tuning_long import PLAN as TEN
from two_deck_live_tuning_half_hour import PLAN,main


class HalfHourLiveTests(unittest.TestCase):
    def test_only_observation_budgets_change_and_entry_remains_inert(self):
        self.assertEqual({k for k in set(TEN)|set(PLAN) if TEN.get(k)!=PLAN.get(k)},
                         {'name','duration_s','rolling_path_limit_m','active_message','half_hour_live_session'})
        self.assertEqual(PLAN['duration_s'],1800.)
        self.assertEqual(PLAN['rolling_path_limit_m'],24.)
        self.assertEqual(PLAN['net_rolling_limit_m'],.30)
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        with self.assertRaises(ValueError):validate_plan_change(TEN,PLAN)
        with self.assertRaises(ValueError):validate_plan_change(PLAN,dict(PLAN,duration_s=2000.))

    def test_thirty_minute_bound_cannot_extend_other_entries(self):
        c=LiveTuningController(TuningChannel(gains(PLAN)))
        c(sample(.005),{0:0.,1:0.},PLAN)
        for bad in [dict(PLAN,duration_s=1800.01),dict(TEN,duration_s=1800.)]:
            c=LiveTuningController(TuningChannel(gains(bad)))
            with self.assertRaisesRegex(Fault,'invalid_live_tuning_plan'):
                c(sample(.005),{0:0.,1:0.},bad)

    def test_identical_commands_and_all_thirty_minute_windows_retained(self):
        c=LiveTuningController(TuningChannel(gains(PLAN)))
        old=LiveTuningController(TuningChannel(gains(TEN)))
        for i in range(1,1201):
            a=sample(i*.005);b=copy.deepcopy(a)
            x=c(a,{0:0.,1:0.},PLAN);y=old(b,{0:0.,1:0.},TEN)
            self.assertEqual(x,y)
            if i>1:self.assertFalse(a['ardupilot_balance']['filter_reset'])
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(c.allocated_torque_packet(mid,sign,x[mid],PLAN),
                                 old.allocated_torque_packet(mid,sign,y[mid],TEN))
        for i in range(180):
            for t in [6.1+10.02*i,16.11+10.02*i]:
                z=copy.deepcopy(a);z['t']=t;z['live_tuning']['state']='READY'
                c.observe_pair(checked_pair(z))
        self.assertEqual(len(c.windows),180)

    def test_both_cumulative_and_original_net_guards_remain(self):
        def guard():return HoldTravel({0:{'position_rad':0.},1:{'position_rad':0.}},{0:1,1:-1},PLAN)
        g=guard()
        with self.assertRaisesRegex(Fault,'wheel_rolling_path_stop'):
            for _ in range(1300):
                for p in [.25,0.]:
                    g.update(0,{'position_rad':p});g.update(1,{'position_rad':-p})
        self.assertGreaterEqual(g.path[0],24.)
        g=guard()
        with self.assertRaisesRegex(Fault,'wheel_net_travel_stop'):
            for i in range(1,33):
                g.update(0,{'position_rad':i*.25});g.update(1,{'position_rad':-i*.25})
        self.assertLess(g.path[0],.32)


if __name__=='__main__':unittest.main()
