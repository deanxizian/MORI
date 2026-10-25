import copy
from contextlib import redirect_stdout
import io
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample,checked_pair
from test_wheel_check import Bus
from two_deck_native_causal_balance import PLAN as BASE,NativeCausalBalanceController
from two_deck_native_observed_balance import PLAN,NativeObservedBalanceController,main


class ObservedNativeTests(unittest.TestCase):
    def test_default_inert_and_control_plan_unchanged(self):
        differences={k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)}
        self.assertEqual(differences,{'name','control_phase','active_message','live_status_window_limit'})
        self.assertEqual(gains(PLAN),gains(BASE))
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_wire_commands_unchanged_while_publishing_diagnostic_terms(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0])
        c=NativeObservedBalanceController(ch)
        prior=NativeCausalBalanceController(TuningChannel(gains(BASE)))
        for i in range(1,1601):
            clock[0]=i*.005;a=sample(clock[0]);b=copy.deepcopy(a)
            speeds={0:.01,1:-.012}
            out=c(a,speeds,PLAN);before=prior(b,speeds,BASE)
            self.assertEqual(out,before)
            for m,s in ((0,1),(1,-1)):
                self.assertEqual(c.allocated_torque_packet(m,s,out[m],PLAN),
                    prior.allocated_torque_packet(m,s,before[m],BASE))
            c.observe_pair(checked_pair(a))
            self.assertEqual(a['ardupilot_balance'],b['ardupilot_balance'])
        info=ch.status()['control_terms']
        self.assertEqual(info['native_velocity_target_rad_s'],
            a['ardupilot_balance']['native_velocity_forward_rad_s'])

    def test_bounded_wire_history_full_summary_and_snapshot_isolation(self):
        clock=[.005];ch=TuningChannel(gains(PLAN),now=lambda:clock[0])
        c=NativeObservedBalanceController(ch)
        a=sample(clock[0]);c(a,{0:0.,1:0.},PLAN)
        c.windows=[dict(index=i) for i in range(120)]
        c.observe_pair(checked_pair(a));state=ch.status()
        self.assertEqual(state['completed_windows'],c.windows[-8:])
        self.assertEqual(state['completed_windows_available'],120)
        self.assertTrue(state['completed_windows_truncated'])
        state['completed_windows'][0]['index']=-1
        state['control_terms']['predicted_net_per_wheel_nm'][0]=999
        self.assertNotEqual(ch.status()['completed_windows'][0]['index'],-1)
        self.assertNotEqual(ch.status()['control_terms']['predicted_net_per_wheel_nm'][0],999)
        self.assertEqual(len(c.summary()['windows']),120)

    def test_legacy_status_history_is_preserved(self):
        ch=TuningChannel(gains(BASE));c=NativeCausalBalanceController(ch)
        a=sample(.005);c(a,{0:0.,1:0.},BASE)
        c.windows=[dict(index=i) for i in range(120)]
        c.observe_pair(checked_pair(a))
        self.assertEqual(len(ch.status()['completed_windows']),120)
        self.assertNotIn('completed_windows_limit',ch.status())

    def test_invalid_status_cap_rejects_before_arm_and_active(self):
        for value in [None,False,True,0,33,8.,'8']:
            for method in ['validate_arm','__call__']:
                c=NativeObservedBalanceController(TuningChannel(gains(PLAN)))
                with self.assertRaisesRegex(Fault,'invalid_live_status_window_limit'):
                    getattr(c,method)(sample(.005),{0:0.,1:0.},dict(PLAN,live_status_window_limit=value))
                self.assertFalse(c.ever_active)

    def test_final_mode_zero_and_fault_does_not_rearm(self):
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase'])
            c=NativeObservedBalanceController(TuningChannel(gains(PLAN),now=bus.now));report={}
            class Cue:
                def check(self):pass
                def tick(self):pass
                def deactivate(self):pass
            def exchange(m):
                original=bus.exchange(m)
                def call(packet,phase):
                    row=original(packet,phase);row['feedback_received_monotonic']=bus.now();return row
                return call
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(PLAN,duration_s=.5),
                controller=c,travel_factory=HoldTravel,indicator=Cue())
            self.assertEqual(report['status'],'FAIL' if fail else 'PASS',report.get('reason'))
            self.assertTrue(report['final_disabled_verified'])
            with self.assertRaises(Fault):c.reset()


if __name__=='__main__':unittest.main()
