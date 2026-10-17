"""Diagnostic packet polarity and mandatory stop behavior, not robot physics."""
import io
import struct
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from air_trial import run,torque_packet
from attitude import Fault
from ground_hold_trial import HoldTravel
from protocol import RATIO
from self_righting_direction_probe import PROBE_PLAN,DirectionProbe,main
from test_attitude_air import CAL
from test_self_righting import pose,TraceIMU
from test_wheel_check import Bus


class DirectionProbeTests(unittest.TestCase):
    def test_default_no_hardware(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
            self.assertEqual(main(['--polarity','original']),0)

    def test_reverse_packet_direction_and_torque_envelope(self):
        for polarity in (-1,1):
            plan=dict(PROBE_PLAN,probe_direction=polarity)
            for sign in (-1.,1.):
                c=DirectionProbe();c(pose(.01,sign*88),{0:0.,1:0.},plan)
                for i in range(1,41):out=c(pose(.01+i*.01,sign*88),{0:0.,1:0.},plan)
                for mid in (0,1):
                    ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(mid,out[mid],plan),4)
                    self.assertGreater(ff*sign*polarity,0.)
                    self.assertLessEqual(abs(ff/256000*RATIO),.12)
                with self.assertRaisesRegex(Fault,'direction_changed'):
                    c(pose(.42,sign*88),{0:0.,1:0.},dict(plan,probe_direction=-polarity))
        for s in (-6.,-3.,0.,3.,6.):
            c=DirectionProbe();c(pose(.01),{0:0.,1:0.})
            out=c(pose(.02),{0:s,1:s})
            ff,_,_,_,kd=struct.unpack_from('<hhihh',torque_packet(0,out[0],PROBE_PLAN),4)
            self.assertLessEqual(abs(ff/256000*RATIO-kd/128000000*RATIO**2*s),.12)

    def test_gyro_motion_stops_both_and_latches(self):
        c=DirectionProbe();c(pose(.01),{0:0.,1:0.})
        with self.assertRaisesRegex(Fault,'gyro_travel_stop'):
            for i in range(1,20):c(pose(.01+i*.01,88,rate=-50),{0:0.,1:0.})
        with self.assertRaisesRegex(Fault,'fault_latched'):c(pose(.2),{0:0.,1:0.})

    def test_runner_ends_diagnostic_disabled_without_claiming_self_righting(self):
        for fault in (False,True):
            bus=Bus(timeout=True,fail=(lambda mid,p,phase:mid==0 and phase=='self_righting_direction_probe') if fault else None)
            report={}
            run({m:bus.exchange(m) for m in (0,1)},TraceIMU(bus,stuck=True),CAL,report,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=PROBE_PLAN,
                controller=DirectionProbe(),travel_factory=HoldTravel)
            self.assertEqual(report['status'],'FAIL' if fault else 'PASS',report.get('reason'))
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(report['controller_summary']['physical_self_righting'],'NOT_TESTED')
            last=max(i for i,(_,_,phase) in enumerate(bus.log) if phase=='self_righting_direction_probe')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[last+1:]))


if __name__=='__main__':unittest.main()
