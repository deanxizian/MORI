import io
import math
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from air_trial import run
from low_speed_stop_probe import StopProbeController
from stop_release_speed_probe import PLAN,main
from test_attitude_air import CAL
from test_self_righting import TraceIMU
from test_wheel_check import Bus


class ReleaseSpeedTests(unittest.TestCase):
    def test_default_has_no_hardware_io(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_runner_releases_and_locks_at_finite_end(self):
        bus=Bus();report={}
        run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,stuck=True),CAL,report,False,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=PLAN,controller=StopProbeController())
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(report['final_disabled_verified'])
        self.assertTrue(report['controller_summary']['zero_torque_phase_seen'])
        self.assertLess(report['elapsed_s'],2.4)
        for s in report['samples']:
            probe=s['attitude']['stop_probe']
            for target in probe['targets_forward_rad_s'].values():self.assertLessEqual(abs(target),3.)
            for value in probe['budget'].get('predicted_net_torque_nm',{}).values():
                self.assertLessEqual(abs(value),.12)

    def release_fixture(self):
        c=StopProbeController();a=dict(t=0.,dt=.01,pitch_deg=90.,pitch_rate_dps=0.,roll_deg=0.,wheel_position_forward_rad={0:0.,1:0.})
        for i in range(100):
            v=min(2.5,i*.1)
            a.update(t=i*.01,wheel_position_forward_rad={m:a['wheel_position_forward_rad'][m]+v*.01 for m in (0,1)})
            c(a,{0:v,1:v},PLAN)
            if c.phase=='CONTROLLED_DECELERATION':return c,a
        self.fail('release not reached')

    def test_25_degree_release_cannot_restart(self):
        c,a=self.release_fixture()
        for i in range(100):
            v=0. if i<30 else -.2
            a.update(t=a['t']+.01,wheel_position_forward_rad={m:a['wheel_position_forward_rad'][m]+v*.01 for m in (0,1)})
            c(a,{0:v,1:v},PLAN)
        self.assertLess(a['wheel_position_forward_rad'][0],math.radians(25.))
        self.assertEqual(c.phase,'ZERO_TORQUE_OBSERVE');self.assertEqual(c.targets,{0:0.,1:0.})

    def test_fault_during_deceleration_latches_immediately(self):
        c,a=self.release_fixture()
        self.assertEqual(c.phase,'CONTROLLED_DECELERATION')
        a.update(t=a['t']+.01,pitch_rate_dps=90.)
        with self.assertRaisesRegex(Exception,'body_rotation_rate_stop'):c(a,{0:2.5,1:2.5},PLAN)
        a.update(pitch_rate_dps=0.)
        with self.assertRaisesRegex(Exception,'fault_latched'):c(a,{0:0.,1:0.},PLAN)

    def test_ramp_reaches_zero_effort_without_restarting(self):
        c,a=self.release_fixture()
        last=c.targets.copy()
        for i in range(1,31):
            v=max(0.,2.5*(1.-i/20.))
            a.update(t=a['t']+.01,wheel_position_forward_rad={m:a['wheel_position_forward_rad'][m]+v*.01 for m in (0,1)})
            c(a,{0:v,1:v},PLAN)
            for m in (0,1):self.assertLessEqual(c.targets[m],last[m]+1e-9)
            last=c.targets.copy()
        self.assertEqual(c.phase,'ZERO_TORQUE_OBSERVE');self.assertEqual(c.kd,0.)


if __name__=='__main__':unittest.main()
