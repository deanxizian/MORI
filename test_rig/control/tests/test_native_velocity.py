import io
import math
import struct
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from air_trial import velocity_packet,run
from attitude import Fault
from protocol import RATIO,crc32_words
from velocity_envelope import velocity_targets
from self_righting_velocity_trial import VELOCITY_PLAN,main
from self_righting_trial import SelfRightingController
from test_attitude_air import CAL
from test_self_righting import TraceIMU
from test_wheel_check import Bus


class NativeVelocityTests(unittest.TestCase):
    def test_default_never_opens_hardware(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_packet_uses_only_velocity_and_damping(self):
        p=dict(VELOCITY_PLAN,native_wheel_damping_nm_per_rad_s=.06)
        for v in (-11.,-1.,0.,1.,11.):
            packet=velocity_packet(1,v,p);ff,speed,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
            self.assertEqual((ff,pos,kp),(0,0,0));self.assertGreater(kd,0)
            self.assertLessEqual(abs(speed*math.tau/(RATIO*2.56)),11.)
            self.assertAlmostEqual(speed*math.tau/(RATIO*2.56),v,delta=.009)
            self.assertEqual(struct.unpack_from('<I',packet,16)[0],crc32_words(packet[:16]))
        with self.assertRaises(Fault):velocity_packet(0,11.1,p)

    def test_quantized_net_torque_budget_bounds_both_velocity_estimates(self):
        p=dict(VELOCITY_PLAN,native_wheel_damping_nm_per_rad_s=.06)
        for v in (-14.,-11.,-8.,0.,8.,11.,14.):
            for offset in (-.7,0.,.7):
                for request in (-.35,0.,.35):
                    speed={0:v,1:-v};pos={0:v+offset,1:-(v+offset)}
                    out,info=velocity_targets({0:request,1:-request},speed,pos,{0:0.,1:0.},.01,p)
                    self.assertAlmostEqual(out[0],-out[1])
                    for mid in (0,1):
                        ff,raw,_,_,kd=struct.unpack_from('<hhihh',velocity_packet(mid,out[mid],p),4)
                        target=raw*math.tau/(RATIO*2.56);damping=kd*RATIO**2/128000000
                        self.assertEqual(ff,0)
                        for estimate in (speed[mid],pos[mid]):
                            self.assertLessEqual(abs(damping*(target-estimate)),.35)

    def test_normal_target_slew_and_impossible_envelope_fail(self):
        out,info=velocity_targets({0:.35,1:-.35},{0:0.,1:0.},{0:0.,1:0.},{0:0.,1:0.},.01,VELOCITY_PLAN)
        self.assertAlmostEqual(out[0],1.5);self.assertAlmostEqual(out[1],-1.5)
        self.assertFalse(info['budget_overrode_slew'])
        with self.assertRaises(Fault):
            velocity_targets({0:0.,1:0.},{0:20.,1:20.},{0:20.,1:20.},{0:0.,1:0.},.01,VELOCITY_PLAN)

    def test_runner_maps_velocity_signs_and_fault_locks_without_rearm(self):
        bus=Bus(fail=lambda m,p,phase:phase=='self_righting' and m==0 and bus.now()>4.5)
        report={};run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,stuck=True),CAL,report,False,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=VELOCITY_PLAN,controller=SelfRightingController())
        self.assertTrue(report['final_disabled_verified'])
        active=[(m,p) for m,p,phase in bus.log if phase=='self_righting']
        self.assertTrue(active)
        for m,p in active:
            ff,speed,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
            self.assertEqual((ff,pos,kp),(0,0,0))
            self.assertLessEqual(abs(speed*math.tau/(RATIO*2.56)),11.)
            self.assertAlmostEqual(kd*RATIO**2/128000000,.06,delta=.001)
        for sample in report['samples']:
            for mid,w in sample.get('wheels',{}).items():
                self.assertIn('command_speed_forward_rad_s',w)
                self.assertAlmostEqual(w['feedback']['speed_rad_s'],w['command_speed_forward_rad_s']*CAL['wheel_signs'][str(mid)],delta=.009)
        last=max(i for i,(_,_,phase) in enumerate(bus.log) if phase=='self_righting')
        self.assertTrue(all((p[2]>>4)&7==0 for _,p,_ in bus.log[last+1:]))

    def test_invalid_velocity_configuration_rejects_before_enable(self):
        for changed in ({'velocity_native_kd_nm_per_rad_s':0.},
                        {'velocity_target_limit_rad_s':12.},
                        {'velocity_target_slew_rad_s2':201.}):
            bus=Bus();report={}
            run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,stuck=True),CAL,report,False,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,
                plan=dict(VELOCITY_PLAN,**changed),controller=SelfRightingController())
            self.assertEqual(bus.maximum_enabled,0)
            self.assertTrue(report['final_disabled_verified'])


if __name__=='__main__':unittest.main()
