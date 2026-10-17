from contextlib import redirect_stdout
import io
import math
import struct
import unittest
from unittest.mock import patch

import wheel_check as check
from protocol import crc32_words


class Bus:
    def __init__(self,fail=None,temp=40,timeout=False):
        self.t=0
        self.fail=fail
        self.temp=temp
        self.log=[]
        self.states={m:dict(mode=0,speed=0.,pos=0.,last=0.,timeout=timeout) for m in (0,1)}
        self.maximum_enabled=0

    def now(self):
        return self.t

    def sleep(self,dt):
        self.t+=dt

    def exchange(self,mid):
        def call(packet,phase):
            self.log.append((mid,packet,phase))
            if self.fail and self.fail(mid,packet,phase):
                self.fail=None
                raise TimeoutError('injected_bus_failure')
            state=self.states[mid]
            state['pos']+=state['speed']*(self.t-state['last'])
            state['last']=self.t
            state['mode']=(packet[2]>>4)&7
            if packet[2]&0x80==0:
                state['timeout']=False
            raw=struct.unpack_from('<h',packet,6)[0]
            state['speed']=raw/2.56*math.tau/check.RATIO if state['mode'] else 0.
            self.maximum_enabled=max(self.maximum_enabled,sum(s['mode']==1 for s in self.states.values()))
            return dict(mode=state['mode'],speed_rad_s=state['speed'],position_rad=state['pos'],
                        temperature_c=self.temp,voltage_v=12,torque_estimate_nm=.01,
                        errors_raw=0,warning_raw=0,timeout_active=state['timeout'])
        return call


class WheelCheckTests(unittest.TestCase):
    def run_bus(self,bus,ack=True):
        report={}
        with redirect_stdout(io.StringIO()):
            check.run({m:bus.exchange(m) for m in (0,1)},report,ack,now=bus.now,sleep=bus.sleep)
        return report

    def test_default_opens_nothing(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(check.main([]),0)

    def test_packet_limits_and_no_position_or_feedforward(self):
        for v in (0,math.radians(30)):
            p=check.packet(1,v)
            self.assertEqual(len(p),20)
            self.assertEqual(p[2],0x91)
            self.assertEqual(struct.unpack_from('<I',p,16)[0],crc32_words(p[:16]))
            torque,speed,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
            self.assertEqual((torque,pos,kp),(0,0,0))
            self.assertGreater(kd,0)
        for v in (float('nan'),-1,1):
            with self.assertRaises(ValueError):
                check.packet(0,v)

    def test_only_one_wheel_enabled_and_both_finally_stopped(self):
        bus=Bus(timeout=True); report=self.run_bus(bus)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(bus.maximum_enabled,1)
        self.assertEqual(report['timeout_cleared_ids'],[0,1])
        for p in report['phases']:
            self.assertTrue(70<p['displacement_deg']<80)

    def test_bus_failure_stops_both_without_rearm(self):
        bus=Bus(fail=lambda mid,p,phase:phase=='direction_check' and mid==0)
        report=self.run_bus(bus)
        self.assertEqual(report['status'],'FAIL')
        self.assertTrue(report['final_disabled_verified'])
        index=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='direction_check')
        self.assertTrue(all((p[2]&0x70)==0 for _,p,_ in bus.log[index+1:]))
        self.assertEqual({mid for mid,_,phase in bus.log[index+1:] if phase=='stop_confirm'},{0,1})

    def test_hot_or_unacknowledged_timeout_never_enables(self):
        for bus,ack in ((Bus(temp=70),True),(Bus(timeout=True),False)):
            report=self.run_bus(bus,ack)
            self.assertEqual(report['status'],'FAIL')
            self.assertTrue(report['final_disabled_verified'])
            self.assertEqual(bus.maximum_enabled,0)


if __name__=='__main__':
    unittest.main()
