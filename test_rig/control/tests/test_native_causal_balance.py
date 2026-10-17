import copy
from contextlib import redirect_stdout
import io
import math
import struct
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import TuningChannel
from live_tuning_policy import gains
from protocol import RATIO,crc32_words
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample
from test_wheel_check import Bus
from two_deck_live_causal_velocity import CausalVelocityLiveController
from two_deck_native_causal_balance import PLAN,NativeCausalBalanceController,main


class NativeCausalBalanceTests(unittest.TestCase):
    def test_default_inert_and_current_gains_original_guards(self):
        from two_deck_live_causal_velocity import PLAN as prior
        differences={k for k in set(prior)|set(PLAN) if prior.get(k)!=PLAN.get(k)}
        self.assertEqual(differences,{'name','ap_kp','ap_kd','native_execution_kd',
            'native_execution_speed_limit_rad_s','control_phase','active_message'})
        self.assertEqual(gains(PLAN),dict(pitch_p=3.25,pitch_i=.6,pitch_d=.05,speed_p=.25))
        self.assertNotIn('operator_held_diagnostic',PLAN)
        with patch('socket.socket',side_effect=AssertionError('socket')),patch(
                'pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)

    def test_single_outer_pid_same_references_and_exact_native_wire_budgets(self):
        c=NativeCausalBalanceController(TuningChannel(gains(PLAN)))
        prior=CausalVelocityLiveController(TuningChannel(gains(PLAN)))
        pid=None;resets=0
        for i in range(1,1601):
            t=i*.005;a=sample(t)
            a.update(pitch_deg=.2+.15*math.sin(3*t),pitch_error_deg=.2+.15*math.sin(3*t),
                pitch_rate_dps=.45*math.cos(3*t),
                wheel_position_forward_rad={0:.008*math.sin(t),1:.009*math.sin(t)})
            b=copy.deepcopy(a);speeds={0:.008*math.cos(t),1:.009*math.cos(t)}
            commands=c(a,speeds,PLAN);prior(b,speeds,PLAN)
            if pid is None:pid=c.pid
            self.assertIs(c.pid,pid);resets+=a['ardupilot_balance']['filter_reset']
            for key in ('velocity_hold','velocity_frame_control','position_hold','stationary_integrator'):
                self.assertEqual(a[key],b[key])
            for key in ('p_nm','i_nm','d_nm','desired_pitch_forward_deg','requested_net_per_wheel_nm'):
                self.assertEqual(a['ardupilot_balance'][key],b['ardupilot_balance'][key])
            for mid,sign in ((0,1),(1,-1)):
                packet=c.allocated_torque_packet(mid,sign,commands[mid],PLAN)
                ff,v,pos,kp,kd=struct.unpack_from('<hhihh',packet,4)
                self.assertEqual((pos,kp),(0,0))
                self.assertEqual(struct.unpack_from('<I',packet,16)[0],crc32_words(packet[:16]))
                forward_ff=sign*ff*RATIO/256000.
                velocity=sign*v*math.tau/(RATIO*2.56)
                damper=kd*RATIO**2/128000000.
                net=forward_ff+damper*(velocity-speeds[mid])
                self.assertLessEqual(abs(forward_ff),.12+1e-12)
                self.assertLessEqual(abs(net),.12+1e-12)
                self.assertLessEqual(abs(velocity),6.)
                self.assertLessEqual(damper,.04)
                self.assertAlmostEqual(net,c.native_allocations[mid].predicted_net_nm)
        self.assertEqual(resets,1)
        with self.assertRaisesRegex(Fault,'configuration_changed'):
            c.allocated_torque_packet(0,1,commands[0],dict(PLAN,native_execution_kd=.4))
        a=sample(8.005);a['wheel_position_forward_rad']={0:0.,1:0.}
        with self.assertRaises(Fault):c(a,{0:6.1,1:0.},PLAN)
        self.assertFalse(c.native_allocations)

    def test_full_arm_active_fault_and_no_rearm_lifecycle(self):
        for link_failure in (False,True):
            bus=Bus(timeout=True,fail=lambda mid,packet,phase:
                link_failure and mid==1 and phase==PLAN['control_phase'])
            channel=TuningChannel(gains(PLAN),now=bus.now)
            c=NativeCausalBalanceController(channel);r={}
            class Cue:
                off=False
                def check(self):pass
                def tick(self):pass
                def deactivate(self):self.off=True
            cue=Cue()
            def exchange(mid):
                original=bus.exchange(mid)
                def call(packet,phase):
                    row=original(packet,phase);row['feedback_received_monotonic']=bus.now();return row
                return call
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),r,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(PLAN,duration_s=.5),
                controller=c,travel_factory=HoldTravel,indicator=cue)
            self.assertEqual(r['status'],'FAIL' if link_failure else 'PASS',r.get('reason'))
            self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
            self.assertTrue(r['controller_reset_before_active'])
            stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[stop:]))
            with self.assertRaises(Fault):c.reset()


if __name__=='__main__':unittest.main()
