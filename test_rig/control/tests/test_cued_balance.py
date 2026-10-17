import copy
import math
import unittest

from air_trial import run
from ground_hold_trial import HoldTravel
from net_torque_adapter import NetTorquePitchController
from test_attitude_air import CAL
from test_wheel_check import Bus
from two_deck_cued_balance import PLAN
from two_deck_net_observe import PLAN as PREVIOUS


class Indicator:
    def __init__(self,bus,fail=False):self.bus=bus;self.fail=fail;self.ticks=0;self.off=False
    def check(self):
        if self.fail and self.ticks>5:raise RuntimeError('cam_ack_lost')
    def tick(self):
        self.check()
        self.ticks+=1
        assert [p for _,_,p in self.bus.log[-2:]]==[PLAN['control_phase']]*2
    def deactivate(self):self.off=True


class HandIMU:
    def __init__(self,bus,active_bad=False,sensor_bad=False):
        self.bus=bus;self.active_bad=active_bad;self.sensor_bad=sensor_bad
    def sample(self):
        self.bus.sleep(.005);t=self.bus.t
        active=any(p==PLAN['control_phase'] for _,_,p in self.bus.log[-4:])
        if self.sensor_bad:raise OSError('sensor_disconnected')
        # Large repositioning acceleration is tolerated only before arming.
        norm=1.8 if t<.3 or (active and self.active_bad) else 1.
        return dict(t_read_complete=t,accel_g=[0,0,norm],gyro_dps=[0,0,0])


class CuedBalanceTests(unittest.TestCase):
    def test_running_guards_and_controller_unchanged(self):
        changed={'name','require_cam_indicator','handheld_wait','arm_stable_s','arm_pitch_limit_deg',
                 'arm_rate_limit_dps','arm_pitch_span_deg','wait_upright_message','active_message'}
        self.assertEqual({k:v for k,v in PLAN.items() if k not in changed},
                         {k:v for k,v in PREVIOUS.items() if k not in changed})
        self.assertFalse(PLAN['capture_start_reference'])

    def fixture(self,*,indicator=True,fail=False,active_bad=False,sensor_bad=False):
        bus=Bus(timeout=True);report={};cue=Indicator(bus,fail) if indicator else None
        run({m:bus.exchange(m) for m in (0,1)},HandIMU(bus,active_bad,sensor_bad),copy.deepcopy(CAL),
            report,True,now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=NetTorquePitchController(),travel_factory=HoldTravel,indicator=cue)
        return bus,report,cue

    def test_hand_adjustment_restarts_dwell_then_cue_follows_real_pairs(self):
        b,r,c=self.fixture()
        self.assertEqual(r['status'],'PASS');self.assertGreater(r['waiting_motion_frames'],0)
        first=next(i for i,(_,p,_) in enumerate(b.log) if p[2]&0x70)
        self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[:first]))
        self.assertGreater(c.ticks,90);self.assertTrue(c.off)
        self.assertTrue(r['final_disabled_verified'])

    def test_missing_indicator_never_enables(self):
        b,r,c=self.fixture(indicator=False)
        self.assertEqual(r['reason'],'cam_indicator_required_before_enable')
        self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log))

    def test_manual_wheel_motion_at_entry_waits_in_mode_zero(self):
        bus=Bus(timeout=True);report={};cue=Indicator(bus)
        def exchange(mid):
            original=bus.exchange(mid)
            def call(packet,phase):
                row=original(packet,phase)
                if bus.t<.7:
                    self.assertEqual((packet[2]>>4)&7,0)
                    row['speed_rad_s']=.3
                return row
            return call
        run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=NetTorquePitchController(),travel_factory=HoldTravel,indicator=cue)
        self.assertEqual(report['status'],'PASS');self.assertGreater(cue.ticks,90)

    def test_sensor_failure_is_not_treated_as_hand_motion(self):
        b,r,c=self.fixture(sensor_bad=True)
        self.assertEqual(r['reason'],'sensor_disconnected')
        self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log));self.assertTrue(c.off)

    def test_active_acceleration_and_indicator_failure_stop_without_rearm(self):
        for options,reason in ((dict(active_bad=True),'acceleration_outside_test_window'),
                               (dict(fail=True),'cam_ack_lost')):
            b,r,c=self.fixture(**options)
            self.assertEqual(r['reason'],reason);self.assertTrue(r['final_disabled_verified'])
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]));self.assertTrue(c.off)


if __name__=='__main__':unittest.main()
