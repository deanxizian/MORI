import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch
from air_trial import health,run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import LiveTuningController,TuningChannel
from live_tuning_policy import gains,validate_plan_change
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_tuning_half_hour import PLAN as PREVIOUS
from two_deck_live_tuning_temp80 import PLAN,main


class Temperature80Tests(unittest.TestCase):
    def test_only_temperature_stop_changes_and_default_is_inert(self):
        self.assertEqual({k for k in set(PLAN)|set(PREVIOUS) if PLAN.get(k)!=PREVIOUS.get(k)},
                         {'name','temperature_limit_c','active_message'})
        self.assertEqual(PLAN['temperature_limit_c'],80)
        self.assertEqual(PREVIOUS['temperature_limit_c'],70)
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        with self.assertRaisesRegex(ValueError,'immutable_plan_field_changed'):
            validate_plan_change(PREVIOUS,PLAN)
        with self.assertRaisesRegex(ValueError,'immutable_plan_field_changed'):
            validate_plan_change(PLAN,dict(PLAN,temperature_limit_c=90))

    def test_temperature_boundary_and_vendor_faults(self):
        row=dict(mode=1,speed_rad_s=0.,position_rad=0.,torque_estimate_nm=.01,
                 voltage_v=12.,temperature_c=79,errors_raw=0,warning_raw=0,timeout_active=False)
        health(row,1,plan=PLAN)
        for t in (80,81,float('nan'),float('inf')):
            with self.assertRaises(Fault):health(dict(row,temperature_c=t),1,plan=PLAN)
        with self.assertRaisesRegex(Fault,'servo_temperature_stop'):
            health(dict(row,temperature_c=70),1,plan=PREVIOUS)
        for field in ('errors_raw','warning_raw'):
            with self.assertRaisesRegex(Fault,'servo_mode_error_or_warning'):
                health(dict(row,**{field:1}),1,plan=PLAN)

    def test_controller_packets_identical_below_old_temperature_limit(self):
        new=LiveTuningController(TuningChannel(gains(PLAN)))
        old=LiveTuningController(TuningChannel(gains(PREVIOUS)))
        for i in range(1,1201):
            a=sample(i*.005);b=copy.deepcopy(a)
            x=new(a,{0:0.,1:0.},PLAN);y=old(b,{0:0.,1:0.},PREVIOUS)
            self.assertEqual(x,y)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(new.allocated_torque_packet(mid,sign,x[mid],PLAN),
                                 old.allocated_torque_packet(mid,sign,y[mid],PREVIOUS))

    def test_either_hot_motor_stops_both_and_never_rearms(self):
        class Cue:
            def __init__(self):self.off=False
            def tick(self):pass
            def check(self):pass
            def deactivate(self):self.off=True
        for hot_id in (0,1):
            bus=Bus(timeout=True,temp=79);report={};cue=Cue()
            channel=TuningChannel(gains(PLAN),now=bus.now)
            active_counts={0:0,1:0}
            def exchange(mid):
                original=bus.exchange(mid)
                def wrapped(packet,phase):
                    row=original(packet,phase);row['feedback_received_monotonic']=bus.now()
                    if phase==PLAN['control_phase']:
                        active_counts[mid]+=1
                        if mid==hot_id and active_counts[mid]>=10:row['temperature_c']=80
                    return row
                return wrapped
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,
                plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
                controller=LiveTuningController(channel),travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(report['reason'],'servo_temperature_stop')
            self.assertTrue(report['final_disabled_verified']);self.assertTrue(cue.off)
            self.assertEqual(bus.maximum_enabled,2)
            stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
            self.assertTrue(all(packet[2]&0x70==0 for _,packet,_ in bus.log[stop:]))
            self.assertEqual(channel.status()['phase'],'STOPPED')


if __name__=='__main__':unittest.main()
