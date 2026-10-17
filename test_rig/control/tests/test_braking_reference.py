import unittest
from attitude import Fault
from ground_ardupilot_balance import ArduPilotBalanceController
from test_two_deck_heading import frame
from two_deck_braking_reference import PLAN,RelativeHeadingController
from two_deck_push_observe import PLAN as BEFORE


class BrakingReferenceTests(unittest.TestCase):
    def test_explicit_opt_in_accepts3deg_but_legacy_and_over3_reject(self):
        for desired in (-3.,3.):
            a=frame(.005,{0:0.,1:0.});a['speed_pitch_reference_deg']=desired
            ArduPilotBalanceController()(a,{0:0.,1:0.},PLAN)
            self.assertAlmostEqual(a['ardupilot_balance']['desired_pitch_forward_deg'],desired)
            for changed in (dict(PLAN,allow_wide_speed_pitch_reference=False),
                            dict(PLAN,speed_pitch_reference_limit_deg=3.01)):
                with self.assertRaisesRegex(Fault,'reference_outside_plan'):
                    ArduPilotBalanceController()(a,{0:0.,1:0.},changed)

    def test_reference_guard_configuration_cannot_change_during_run(self):
        for original,changed in ((BEFORE,PLAN),(PLAN,dict(PLAN,speed_pitch_reference_limit_deg=2.9))):
            c=ArduPilotBalanceController();a=frame(.005,{0:0.,1:0.})
            c(a,{0:0.,1:0.},original)
            with self.assertRaisesRegex(Fault,'parameters_changed'):
                c(frame(.01,{0:0.,1:0.}),{0:0.,1:0.},changed)

    def test_braking_reference_and_integer_output_remain_bounded_at_high_speed(self):
        for speed in (-5.9,5.9):
            c=RelativeHeadingController()
            refs=[]
            for i in range(1,201):
                a=frame(i*.005,{0:speed*i*.005,1:speed*i*.005})
                commands=c(a,{0:speed,1:speed},PLAN)
                ref=a['speed_pitch_reference_deg'];refs.append(ref)
                self.assertLessEqual(abs(ref),3.)
                if i>1:self.assertLessEqual(abs(ref-refs[-2]),6.*.005+1e-12)
                for m in (0,1):
                    c.allocated_torque_packet(m,1 if m==0 else -1,commands[m],PLAN)
                    self.assertLessEqual(abs(c.allocations[m].feedforward_nm),.12+1e-12)
                    self.assertLessEqual(abs(c.allocations[m].predicted_net_nm),.12+1e-12)
            self.assertAlmostEqual(refs[-1],-3. if speed>0 else 3.)


if __name__=='__main__':unittest.main()
