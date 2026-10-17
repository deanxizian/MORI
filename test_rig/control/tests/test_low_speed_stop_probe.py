import io
import math
import struct
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from air_trial import run
from low_speed_stop_probe import main,make_plan,StopProbeController
from self_righting_velocity_trial import main as old_velocity_main
from self_righting_rate_profile import main as old_rate_main
from test_attitude_air import CAL
from test_self_righting import TraceIMU
from test_wheel_check import Bus
from protocol import RATIO


class StopProbeTests(unittest.TestCase):
    def test_default_no_hardware_and_previous_rising_entries_retired(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        for entry,flag in ((old_velocity_main,'--run-single-self-righting-velocity'),(old_rate_main,'--run-single-self-righting-rate-profile')):
            with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                entry([flag])

    def test_long_probe_requires_release_and_angle_limit_latches(self):
        with self.assertRaises(ValueError):make_plan('lock',2.)
        p=make_plan('release',2.);c=StopProbeController()
        for i in range(17):
            a=dict(t=i*.02,dt=.02,pitch_deg=90.,pitch_rate_dps=0.,roll_deg=0.,
                   wheel_position_forward_rad={0:i*.03,1:i*.03})
            c(a,{0:0.,1:0.},p)
        self.assertEqual(c.phase,'ZERO_TORQUE_OBSERVE')
        self.assertEqual(c.kd,0.)
        a.update(t=.34,wheel_position_forward_rad={0:0.,1:0.})
        c(a,{0:0.,1:0.},p)
        self.assertEqual(c.phase,'ZERO_TORQUE_OBSERVE')
        self.assertEqual(c.targets,{0:0.,1:0.})

    def run_style(self,style,bus):
        report={};run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,stuck=True),CAL,report,False,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=make_plan(style),controller=StopProbeController())
        return report

    def test_normal_release_has_no_ff_stiffness_or_damping_then_locks(self):
        bus=Bus();r=self.run_style('release',bus)
        self.assertEqual(r['status'],'PASS');self.assertTrue(r['final_disabled_verified'])
        self.assertTrue(r['controller_summary']['zero_torque_phase_seen'])
        nzero=0
        for mid,packet,phase in bus.log:
            if phase!='low_speed_stop_probe':continue
            ff,v,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
            self.assertEqual((ff,pos,kp),(0,0,0));self.assertTrue(packet[2]&128)
            self.assertLessEqual(abs(v*math.tau/(2.56*RATIO)),.8)
            if kd==0:self.assertEqual(v,0);nzero+=1
        self.assertGreater(nzero,50)

    def test_direct_lock_comparison_has_no_release_phase(self):
        bus=Bus();r=self.run_style('lock',bus)
        self.assertEqual(r['status'],'PASS');self.assertTrue(r['final_disabled_verified'])
        self.assertFalse(r['controller_summary']['zero_torque_phase_seen'])
        self.assertLess(r['elapsed_s'],.65)

    def test_real_fault_still_locks_without_coast_or_rearm(self):
        bus=Bus(fail=lambda m,p,phase:phase=='low_speed_stop_probe' and m==0)
        r=self.run_style('release',bus)
        self.assertEqual(r['status'],'FAIL');self.assertTrue(r['final_disabled_verified'])
        i=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='low_speed_stop_probe')
        self.assertTrue(all(((p[2]>>4)&7)==0 for _,p,_ in bus.log[i+1:]))


if __name__=='__main__':unittest.main()
