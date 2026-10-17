import copy
from contextlib import redirect_stdout
import io
import json
import math
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from air_trial import run
from attitude import Fault
from ground_hold_trial import HoldTravel
from live_tuning import LiveTuningController,LocalTuningServer,TuningChannel,decode_request
from live_tuning_policy import gains,with_gains,validate_plan_change,validate_set
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_two_deck_heading import frame
from test_wheel_check import Bus
from two_deck_live_tuning import PLAN,main
from two_deck_trim_pitch_gain_325 import PLAN as BASE
from two_deck_velocity_diagnostics import VelocityDiagnosticsController


def request(ch,revision=0,key='pitch_p',value=3.0,ramp=2.,rid='change-1'):
    return dict(op='set',session=ch.session,expected_revision=revision,
                request_id=rid,key=key,value=value,ramp_s=ramp)


def sample(t):
    a=frame(t,{0:0.,1:0.});a.update(pitch_deg=.2*math.sin(t),pitch_error_deg=.2*math.sin(t),
        wheel_feedback_received_monotonic={0:t-.003,1:t-.002})
    return a


def checked_pair(a):
    return dict(attitude=a,wheels={m:dict(feedback=dict(temperature_c=40,mode=1,speed_rad_s=0.)) for m in (0,1)},
                rolling_equivalent=dict(forward_offset_m={0:0.,1:0.}))


class LivePolicyTests(unittest.TestCase):
    def test_default_inert_and_all_guard_fields_identical_to_selected_baseline(self):
        with patch('socket.socket',side_effect=AssertionError('socket I/O')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file I/O')),redirect_stdout(io.StringIO()):
            self.assertEqual(main([]),0)
        self.assertEqual({k for k in set(BASE)|set(PLAN) if BASE.get(k)!=PLAN.get(k)},
            {'name','duration_s','allow_live_tuning','control_phase','active_message'})
        self.assertEqual(PLAN['duration_s'],300.)

    def test_rejects_guard_changes_large_steps_nonfinite_and_session_replays(self):
        ch=TuningChannel(gains(PLAN),session='test')
        for change in [dict(temperature_limit_c=80),dict(duration_s=600),dict(ap_imax=1.),
                       dict(output_scale_nm=.2),dict(allow_live_tuning=False),dict(ap_kp=4./.12)]:
            with self.assertRaises(ValueError):validate_plan_change(PLAN,dict(PLAN,**change))
        for delta in [dict(value=float('nan')),dict(value=True),dict(value=2.75),dict(ramp_s=0),
                      dict(key='temperature_limit_c'),dict(session='old'),dict(expected_revision=True),
                      dict(expected_revision=1),dict(extra='ignored')]:
            with self.assertRaises(ValueError):validate_set(dict(request(ch),**delta),ch.session,0,gains(PLAN))
        for raw in [b'{"op":"status","op":"set"}',b'{"x":NaN}']:
            with self.assertRaises(ValueError):decode_request(raw)

    def test_explicit_retune_preserves_integrator_filters_and_pid_identity(self):
        c=VelocityDiagnosticsController()
        for i in range(1,101):c(sample(i*.005),{0:0.,1:0.},PLAN)
        before=copy.deepcopy(c.pid.__dict__);pid=c.pid
        updated=with_gains(PLAN,dict(gains(PLAN),pitch_p=3.,pitch_i=.45,pitch_d=.08))
        c.apply_live_gains(PLAN,updated)
        self.assertIs(c.pid,pid)
        for k,v in before.items():
            if k not in ('kp','ki','kd'):self.assertEqual(c.pid.__dict__[k],v)
        legacy=VelocityDiagnosticsController();legacy(sample(.005),{0:0.,1:0.},BASE)
        with self.assertRaisesRegex(Fault,'not_enabled'):legacy.apply_live_gains(BASE,dict(BASE,ap_kp=3./.12))
        with self.assertRaisesRegex(Fault,'parameters_changed'):
            legacy(sample(.01),{0:0.,1:0.},dict(BASE,ap_kp=3./.12))


class LiveControlTests(unittest.TestCase):
    def test_no_update_is_exact_packet_parity_with_selected_controller(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0])
        a=LiveTuningController(ch);b=VelocityDiagnosticsController()
        for i in range(1,1201):
            clock[0]=i*.005;x=sample(clock[0]);y=copy.deepcopy(x)
            ca=a(x,{0:0.,1:0.},PLAN);cb=b(y,{0:0.,1:0.},BASE)
            self.assertEqual(ca,cb)
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(a.allocated_torque_packet(mid,sign,ca[mid],PLAN),
                                 b.allocated_torque_packet(mid,sign,cb[mid],BASE))
            a.observe_pair(checked_pair(x))
        self.assertEqual(ch.status()['phase'],'ACTIVE')

    def test_smooth_revision_keeps_pid_and_records_only_settled_windows(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0]);c=LiveTuningController(ch)
        pid=None;trajectory=[]
        for i in range(1,4201):
            clock[0]=i*.005
            if i==1201:self.assertEqual(ch.submit(request(ch))['status'],'QUEUED')
            a=sample(clock[0]);out=c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            if pid is None:pid=c.pid
            self.assertIs(pid,c.pid)
            if i>1:self.assertFalse(a['ardupilot_balance']['filter_reset'])
            trajectory.append(a['live_tuning']['current']['pitch_p'])
            for mid,sign in ((0,1),(1,-1)):
                self.assertEqual(len(c.allocated_torque_packet(mid,sign,out[mid],PLAN)),20)
                self.assertLessEqual(abs(c.allocations[mid].feedforward_nm),.12)
                self.assertLessEqual(abs(c.allocations[mid].predicted_net_nm),.12)
        self.assertEqual(trajectory[1200],3.25)
        self.assertAlmostEqual(trajectory[-1],3.)
        self.assertLessEqual(max(abs(y-x) for x,y in zip(trajectory,trajectory[1:])),.25*.005/2+1e-12)
        self.assertEqual([e['status'] for e in c.events],['RAMP_STARTED','APPLIED'])
        self.assertEqual(c.revision,1);self.assertTrue(c.windows)
        self.assertTrue(all(w['revision']==1 and w['start_elapsed_s']>=10 for w in c.windows))
        with self.assertRaises(ValueError):ch.submit(request(ch))
        with self.assertRaisesRegex(Fault,'cannot_reset'):c.reset()

    def test_outside_update_window_rejects_request_without_reset_or_rearm(self):
        clock=[0.];ch=TuningChannel(gains(PLAN),now=lambda:clock[0]);c=LiveTuningController(ch)
        for i in range(1,1201):
            clock[0]=i*.005;a=sample(clock[0]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
        ch.submit(request(ch));a=sample(6.005);a.update(pitch_deg=6.,pitch_error_deg=6.)
        pid=c.pid;c(a,{0:0.,1:0.},PLAN)
        self.assertIs(c.pid,pid);self.assertEqual(c.revision,0)
        self.assertEqual(gains(c.runtime_plan),gains(PLAN));self.assertEqual(c.last_result['status'],'REJECTED')

    def run_fixture(self,kind):
        bus=Bus(timeout=True);ch=TuningChannel(gains(PLAN),now=bus.now)
        c=LiveTuningController(ch);report={}
        class Cue:
            ticks=0;off=False
            def check(self):pass
            def tick(self):
                self.ticks+=1
                if self.ticks==20:
                    if kind=='active_disarm':ch.disarm.set()
                    if kind=='channel_failure':ch.failed.set()
            def deactivate(self):self.off=True
        cue=Cue()
        def exchange(mid):
            original=bus.exchange(mid)
            def wrapped(packet,phase):
                row=original(packet,phase);row['feedback_received_monotonic']=bus.now()
                if kind=='waiting_disarm' and phase=='wait_upright_disabled':ch.disarm.set()
                return row
            return wrapped
        run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),report,True,
            now=bus.now,sleep=bus.sleep,display=lambda _:None,
            plan=dict(PLAN,duration_s=.5,post_stop_observation_s=0.),
            controller=c,travel_factory=HoldTravel,indicator=cue)
        return bus,report,ch,cue

    def test_waiting_disarm_never_enables_and_active_stop_never_rearms(self):
        for kind,reason in [('waiting_disarm','operator_disarm_requested'),
                            ('active_disarm','operator_disarm_requested'),
                            ('channel_failure','live_tuning_channel_failed')]:
            b,r,ch,cue=self.run_fixture(kind)
            self.assertEqual(r['reason'],reason);self.assertTrue(r['final_disabled_verified']);self.assertTrue(cue.off)
            if kind=='waiting_disarm':self.assertEqual(b.maximum_enabled,0)
            stop=next(i for i,(_,_,p) in enumerate(b.log) if p=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in b.log[stop:]))
            self.assertEqual(ch.status()['phase'],'STOPPED')

    def test_normal_finite_completion_publishes_stopped(self):
        b,r,ch,cue=self.run_fixture('normal')
        self.assertEqual(r['status'],'PASS');self.assertTrue(r['final_disabled_verified'])
        self.assertEqual(ch.status()['phase'],'STOPPED');self.assertTrue(cue.off)


class LocalTransportTests(unittest.TestCase):
    def test_private_socket_rejects_bad_writes_and_disconnect_keeps_channel_alive(self):
        ch=TuningChannel(gains(PLAN),session='transport-test')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'control.sock'
            def call(raw):
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
                    client.settimeout(.5);client.connect(str(path));client.sendall(raw+b'\n')
                    data=b''
                    while b'\n' not in data:data+=client.recv(8192)
                    return json.loads(data.split(b'\n',1)[0])
            with LocalTuningServer(ch,path):
                self.assertEqual(path.stat().st_mode&0o777,0o600)
                self.assertEqual(call(b'{"op":"status"}')['status'],'PASS')
                self.assertEqual(call(json.dumps(request(ch)).encode())['status'],'REJECTED')
                with self.assertRaises(BlockingIOError):
                    with LocalTuningServer(TuningChannel(gains(PLAN)),path):pass
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:client.connect(str(path))
                self.assertEqual(call(b'{"x":NaN}')['status'],'REJECTED')
                self.assertFalse(ch.failed.is_set())
                ch.publish(dict(phase='ACTIVE',tuning_state='READY',revision=0,current=gains(PLAN)))
                self.assertEqual(call(json.dumps(request(ch)).encode())['status'],'QUEUED')
                self.assertEqual(call(json.dumps(request(ch,rid='change-2')).encode())['status'],'REJECTED')
                self.assertEqual(call(b'{"op":"disarm","session":"old"}')['status'],'REJECTED')
                self.assertFalse(ch.disarm.is_set())
                self.assertEqual(call(b'{"op":"disarm","session":"transport-test"}')['status'],'DISARM_REQUESTED')
                self.assertTrue(ch.disarm.is_set())
            self.assertFalse(path.exists())

    def test_stale_snapshot_rejects_new_gain(self):
        now=[0.];ch=TuningChannel(gains(PLAN),now=lambda:now[0])
        ch.publish(dict(phase='ACTIVE',tuning_state='READY',revision=0,current=gains(PLAN)))
        now[0]=1.
        with self.assertRaisesRegex(ValueError,'not_ready'):ch.submit(request(ch))


if __name__=='__main__':unittest.main()
