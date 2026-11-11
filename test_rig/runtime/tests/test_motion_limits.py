import random
import unittest
from motion_limits import coupled_reference


class MotionLimitsTests(unittest.TestCase):
    def test_random_steps_keep_envelope_and_each_axis_between_old_and_candidate(self):
        rng=random.Random(184)
        old=(0.,0.)
        for _ in range(10000):
            candidate=(old[0]+rng.uniform(-.002,.002),
                       old[1]+rng.uniform(-.08,.08))
            new=coupled_reference(*old,*candidate,.04)
            self.assertLessEqual(abs(new[0])/.04+abs(new[1])/2,5.+1e-10)
            for o,c,n in zip(old,candidate,new):
                self.assertGreaterEqual(n,min(o,c)-1e-10)
                self.assertLessEqual(n,max(o,c)+1e-10)
                if abs(c)<=abs(o):self.assertAlmostEqual(n,c)
            old=new

    def test_full_budget_brakes_one_axis_and_gives_room_to_other(self):
        v,turn=coupled_reference(.16,2.,.1585,2.08,.04)
        self.assertAlmostEqual(v,.1585)
        self.assertGreater(turn,2.)
        self.assertAlmostEqual(abs(v)/.04+abs(turn)/2,5.)
