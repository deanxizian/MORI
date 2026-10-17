import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from air_trial import run
from ground_hold_trial import HoldTravel
from test_attitude_air import CAL
from test_cued_balance import Indicator
from test_wheel_check import Bus
from two_deck_heading_hold import RelativeHeadingController
from two_deck_push_observe import PLAN,main


class PushIMU:
    def __init__(self,bus,kind):self.bus=bus;self.kind=kind;self.active_t=None
    def sample(self):
        self.bus.sleep(.005);t=self.bus.now()
        active=any(p==PLAN['control_phase'] for _,_,p in self.bus.log[-4:])
        if active and self.active_t is None:self.active_t=t
        dt=t-self.active_t if self.active_t is not None else -1.
        disturbed=.04<=dt<(.055 if self.kind=='pulse' else .2)
        accel=[0.,0.,1.]
        if disturbed:
            accel={'pulse':[1.48,.588,1.632],'sustained':[1.48,.588,1.632],
                   'impact':[0.,0.,3.1],'freefall':[0.,0.,.1],
                   'nan':[0.,0.,float('nan')]}[self.kind]
        return dict(t_read_complete=t,accel_g=accel,gyro_dps=[0.,0.,0.])


class PushTransientTests(unittest.TestCase):
    def case(self,kind,opt_in=True):
        b=Bus(timeout=True);r={};cue=Indicator(b)
        def tick():cue.check();cue.ticks+=1
        cue.tick=tick
        run({m:b.exchange(m) for m in (0,1)},PushIMU(b,kind),copy.deepcopy(CAL),r,True,
            now=b.now,sleep=b.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.3,post_stop_observation_s=0.,
                      active_imu_acceleration_transients=opt_in),
            controller=RelativeHeadingController(),travel_factory=HoldTravel,indicator=cue)
        self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
        stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
        self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))
        return r

    def test_default_inert(self):
        with patch('pathlib.Path.read_bytes',side_effect=AssertionError('IO')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_actual_push_shaped_pulse_uses_gyro_then_resumes_gravity(self):
        r=self.case('pulse');self.assertEqual(r['status'],'PASS')
        a=[s['attitude'] for s in r['samples']]
        transient=[v for v in a if v['dynamic_acceleration_window']]
        self.assertGreaterEqual(len(transient),2)
        self.assertTrue(all(v['gravity_correction_weight']==0 for v in transient))
        self.assertTrue(all(abs(v['pitch_deg'])<1e-9 and abs(v['roll_deg'])<1e-9 for v in transient))
        self.assertFalse(a[-1]['dynamic_acceleration_window'])
        self.assertGreater(a[-1]['gravity_correction_weight'],0)

    def test_non_opted_profile_keeps_original_acceleration_rejection(self):
        self.assertEqual(self.case('pulse',False)['reason'],'acceleration_outside_test_window')

    def test_sustained_acceleration_and_large_impact_and_freefall_stop(self):
        for kind,reason in (('sustained','sustained_dynamic_acceleration'),
                            ('impact','acceleration_outside_dynamic_window'),
                            ('freefall','acceleration_outside_dynamic_window'),
                            ('nan','nonfinite_control_value')):
            self.assertEqual(self.case(kind)['reason'],reason)


if __name__=='__main__':unittest.main()
