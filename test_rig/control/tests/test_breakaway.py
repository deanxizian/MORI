from contextlib import redirect_stdout
import io
import math
import struct
import unittest
from unittest.mock import patch

import breakaway as check
from test_attitude_air import CAL


class Bus:
    def __init__(self,stall=False):
        self.t=0.;self.stall=stall;self.log=[];self.max_enabled=0
        self.states={m:dict(mode=0,v=0.,p=math.tau-.0001,t=0.) for m in (0,1)}
    def now(self):return self.t
    def sleep(self,dt):self.t+=dt
    def exchange(self,mid):
        def call(packet,phase):
            self.log.append((mid,packet,phase));s=self.states[mid]
            s['p']+=s['v']*(self.t-s['t']);s['t']=self.t
            s['mode']=(packet[2]>>4)&7
            raw,_,_,_,raw_kd=struct.unpack_from('<hhihh',packet,4)
            torque=raw/256000*check.RATIO
            kd=raw_kd/128000000*check.RATIO**2
            s['v']=(math.copysign(max(0,abs(torque)-.035),torque)/kd if s['mode'] and kd and not self.stall else 0.)
            self.max_enabled=max(self.max_enabled,sum(v['mode']==1 for v in self.states.values()))
            return dict(id=mid,mode=s['mode'],speed_rad_s=s['v'],position_rad=s['p'],absolute_output_rad=s['p']%math.tau,
                        torque_estimate_nm=torque,voltage_v=12.,temperature_c=40,errors_raw=0,warning_raw=0,timeout_active=False)
        return call


class BreakawayTests(unittest.TestCase):
    def test_default_is_no_io(self):
        with patch('builtins.open',side_effect=AssertionError('I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(check.main([]),0)

    def test_four_planned_directions_stop_on_output_motion(self):
        bus=Bus();report={}
        check.run({m:bus.exchange(m) for m in (0,1)},CAL,report,True,now=bus.now,sleep=bus.sleep,display=lambda s:None)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(bus.max_enabled,1)
        self.assertEqual([(p['id'],p['protocol_direction']) for p in report['phases']],[(0,1),(0,-1),(1,-1),(1,1)])
        self.assertTrue(all(p['feedforward_at_detection_nm']<=.08 for p in report['phases']))
        self.assertTrue(all(abs(p['samples'][-1]['output_delta_deg'])<10 for p in report['phases']))

    def test_stall_does_not_raise_cap_or_advance_to_other_wheel(self):
        bus=Bus(stall=True);report={}
        check.run({m:bus.exchange(m) for m in (0,1)},CAL,report,True,now=bus.now,sleep=bus.sleep,display=lambda s:None)
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(report['reason'],'no_breakaway_within_fixed_cap')
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(len(report['phases']),1)
        self.assertFalse(any(mid==1 and packet[2]&0x70 for mid,packet,_ in bus.log))

    def test_mode_change_absolute_sensor_shift_is_not_reverse_motion(self):
        bus=Bus();report={};exchanges={}
        def with_shift(base):
            def call(packet,phase):
                row=base(packet,phase)
                if row['mode']==1:
                    # About 0.86 deg on mode change plus 0.29 deg during the
                    # ramp, without corresponding reverse rotor movement.
                    shift=.015+(.005 if phase=='torque_ramp' else 0)
                    row['absolute_output_rad']=(row['absolute_output_rad']+shift)%math.tau
                return row
            return call
        for m in (0,1):exchanges[m]=with_shift(bus.exchange(m))
        check.run(exchanges,CAL,report,True,now=bus.now,sleep=bus.sleep,display=lambda s:None)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(report['final_disabled_verified'])
        self.assertEqual(len(report['phases']),4)


if __name__=='__main__':unittest.main()
