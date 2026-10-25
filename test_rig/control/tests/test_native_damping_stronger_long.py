import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from air_trial import run
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_wheel_check import Bus
from two_deck_native_damping_stronger import PLAN as BASE,StrongerNativeDampingController
from two_deck_native_damping_stronger_long import PLAN,main


class StrongerDampingLongTests(unittest.TestCase):
    def test_long_profile_retains_every_guard_and_default_no_io(self):
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
            {'name','duration_s','control_phase','active_message'})
        self.assertEqual(gains(PLAN),gains(BASE))
        self.assertTrue(PLAN['half_hour_live_session']);self.assertEqual(PLAN['duration_s'],1800.)
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_same_runner_reaches_finite_stop_and_fault_cannot_rearm(self):
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase'])
            c=StrongerNativeDampingController(TuningChannel(gains(PLAN),now=bus.now));report={}
            class Cue:
                def check(self):pass
                def tick(self):pass
                def deactivate(self):pass
            def exchange(m):
                call=bus.exchange(m)
                def wrapped(packet,phase):
                    row=call(packet,phase);row['feedback_received_monotonic']=bus.now();return row
                return wrapped
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(PLAN,duration_s=.5),
                controller=c,travel_factory=HoldTravel,indicator=Cue())
            self.assertEqual(report['status'],'FAIL' if fail else 'PASS',report.get('reason'))
            self.assertTrue(report['final_disabled_verified'])
            stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[stop:]))
            with self.assertRaisesRegex(RuntimeError,'cannot_reset'):c.reset()


if __name__=='__main__':unittest.main()
