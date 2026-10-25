import copy,io,math,struct,unittest,threading,subprocess,time,types
from contextlib import redirect_stdout,ExitStack
from unittest.mock import patch
from air_trial import run
from attitude import Fault
from live_tuning import TuningChannel
from live_tuning_policy import gains,with_gains
from protocol import RATIO
from remote_drive_keys import Keys,LinkProbe,KeyWorker,ADDRESS
from two_deck_native_240_speed025 import PLAN as OLD,NativeDampingController
from two_deck_remote_drive import PLAN,RemoteDriveController,RemoteTravel,RemoteVelocityReference,DriveVelocityProfile,main
from test_attitude_air import CAL
from test_cued_balance import HandIMU
from test_live_tuning import sample,checked_pair
from test_wheel_check import Bus

class KeyTests(unittest.TestCase):
    def test_link_probe_timeout_recovers_and_aged_link_is_neutral(self):
        now=[1.];answers=iter([subprocess.TimeoutExpired('bluetoothctl',.3),True])
        def query():
            value=next(answers)
            if isinstance(value,Exception):raise value
            return value
        p=LinkProbe(threading.Event(),query=query,now=lambda:now[0])
        p.sample_once();self.assertFalse(p.read(1.)[0]);self.assertEqual(p.errors,1)
        now[0]=1.5;p.sample_once();self.assertTrue(p.read(1.6)[0])
        self.assertFalse(p.read(2.31)[0]);self.assertFalse(p.read(1.4)[0])
    def test_evdev_heartbeat_does_not_wait_for_bluez_and_eagain_keeps_device(self):
        k=Keys();now=time.monotonic();k.attach(now,[]);k.event(103,1,now)
        d=types.SimpleNamespace(read=lambda:(_ for _ in ()).throw(BlockingIOError()),active_keys=lambda:[103])
        w=KeyWorker(k,{})
        with patch('remote_drive_keys.select.select',return_value=([d],[],[])),patch('remote_drive_keys.subprocess.run',side_effect=AssertionError('BlueZ in input reader')):
            w.consume_device(d,now)
        self.assertEqual(k.read(time.monotonic())[4],1)
        self.assertEqual(k.since[103],now)
    def test_worker_recovers_device_error_but_held_reconnect_requires_release(self):
        k=Keys();report={};w=KeyWorker(k,report);observed=[];opened=[]
        class Device:
            uniq=ADDRESS;path='/fake';name='fake remote'
            def __init__(self,path):opened.append(self)
            def grab(self):pass
            def active_keys(self):return [103]
            def close(self):pass
        def consume(d,now):
            if len(opened)==1:raise OSError('injected device loss')
            observed.append(k.read(time.monotonic())[4])
            k.publish(time.monotonic(),[]);k.event(103,1,time.monotonic());k.publish(time.monotonic(),[103])
            observed.append(k.read(time.monotonic())[4]);w.stop.set()
        fake=types.SimpleNamespace(list_devices=lambda:['/fake'],InputDevice=Device)
        with ExitStack() as st:
            st.enter_context(patch.dict('sys.modules',evdev=fake))
            for name in ['sched_setscheduler','sched_setaffinity','setpriority','sched_param']:
                st.enter_context(patch('os.'+name,create=True))
            st.enter_context(patch('os.SCHED_OTHER',0,create=True))
            st.enter_context(patch.object(w.link_probe,'run',return_value=None))
            st.enter_context(patch.object(w.link_probe,'read',return_value=(True,None)))
            st.enter_context(patch.object(w,'consume_device',side_effect=consume))
            w.run()
        self.assertEqual(observed,[0,1]);self.assertEqual(len(opened),2)
        self.assertEqual(report['input_errors'],1);self.assertIn('injected device loss',report['last_input_error'])
        self.assertFalse(k.connected);self.assertEqual(k.diagnostics['phase'],'stopped')
    def test_directions_opposition_stop_and_continuous_hold(self):
        k=Keys();k.attach(0,[])
        for code,axis,value in [(103,4,1),(108,4,-1),(105,5,-1),(106,5,1)]:
            k.event(code,1,.01);k.publish(.01,[code]);self.assertEqual(k.read(.01)[axis],value)
            k.event(code,0,.02);k.publish(.02,[]);self.assertEqual(k.read(.02)[4:6],(0,0))
        k.event(103,1,.1);k.publish(.1,[103]);k.event(108,1,.2);k.publish(.2,[103,108]);self.assertEqual(k.read(.2)[4],0)
        k.event(158,1,.3);k.publish(.3,[103,108,158]);self.assertTrue(k.read(.3)[2])
        k.publish(.4,[]);k.event(103,1,1.);k.publish(1.,[103])
        for t in [1.5,2.,2.5,3.01]:k.event(103,2,t);k.publish(t,[103])
        self.assertEqual(k.read(3.01)[4],1);self.assertFalse(k.read(3.01)[2])
        k.publish(3.1,[]);k.event(103,1,3.2);k.publish(3.2,[103]);self.assertEqual(k.read(3.2)[4],1)
    def test_all_directions_hold_30s_with_fresh_state_then_release_or_loss(self):
        for code,axis,sign in [(103,4,1),(108,4,-1),(105,5,-1),(106,5,1)]:
            k=Keys();k.attach(0.,[]);k.event(code,1,.01)
            for i in range(1,1501):
                now=i*.02;k.event(code,2,now);k.publish(now,[code])
                self.assertEqual(k.read(now)[axis],sign)
            self.assertEqual(k.read(30.151)[4:6],(0,0))
            k.event(code,0,30.16);k.publish(30.16,[])
            self.assertEqual(k.read(30.16)[4:6],(0,0))
            k.event(code,1,30.2);k.publish(30.2,[code]);k.disconnect(30.21)
            self.assertEqual(k.read(30.21)[4:6],(0,0))
            k.attach(30.3,[code]);k.event(code,2,30.31);k.publish(30.31,[code])
            self.assertEqual(k.read(30.31)[4:6],(0,0))

    def test_disconnect_stale_sync_loss_and_held_reconnect_never_resume(self):
        k=Keys();k.attach(0,[103]);self.assertEqual(k.read(0)[4],0)
        k.publish(.1,[]);k.event(103,1,.2);k.publish(.2,[103]);self.assertEqual(k.read(.2)[4],1)
        self.assertEqual(k.read(.351)[4],0);self.assertEqual(k.read(.1)[4],0)
        k.disconnect(.4);self.assertEqual(k.read(.4)[4:6],(0,0))
        k.attach(.5,[103]);k.event(103,2,.6);k.publish(.6,[103]);self.assertEqual(k.read(.6)[4],0)
        k.publish(.7,[]);k.publish(.8,[106]);self.assertTrue(k.read(.8)[2]) # missing press

class RemoteTests(unittest.TestCase):
    def test_default_inert_selected_gains_and_non_distance_limits_preserved(self):
        self.assertEqual(gains(PLAN),dict(pitch_p=3.5,pitch_i=.15,pitch_d=.15,speed_p=.35))
        self.assertEqual({k for k in PLAN if PLAN[k]!=OLD.get(k)},
            {'name','ap_ki','ap_kd','speed_kp_rad_per_m_s','control_phase','active_message','net_rolling_limit_m','rolling_path_limit_m'})
        self.assertIsNone(PLAN['net_rolling_limit_m']);self.assertIsNone(PLAN['rolling_path_limit_m'])
        with patch('socket.socket',side_effect=AssertionError('socket')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('file')),redirect_stdout(io.StringIO()):self.assertEqual(main([]),0)
    def test_no_input_exact_packet_parity_with_frozen_selected_gains(self):
        base=with_gains(OLD,gains(PLAN));t=[0.]
        a=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),Keys())
        b=NativeDampingController(TuningChannel(gains(base),now=lambda:t[0]))
        for i in range(1,1201):
            t[0]=i*.005;x=sample(t[0]);y=copy.deepcopy(x)
            ca=a(x,{0:0.,1:0.},PLAN);cb=b(y,{0:0.,1:0.},base)
            for mid,sign in [(0,1),(1,-1)]:self.assertEqual(a.allocated_torque_packet(mid,sign,ca[mid],PLAN),b.allocated_torque_packet(mid,sign,cb[mid],base))
            a.observe_pair(checked_pair(x));b.observe_pair(checked_pair(y))
    def test_reference_sign_release_ramps_pid_identity_and_wire_budgets(self):
        k=Keys();k.attach(0,[]);t=[0.];c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k);pid=None
        for i in range(1,501):
            t[0]=i*.005
            if i==2:k.event(103,1,t[0])
            if i==180:k.event(103,0,t[0])
            if i==300:k.event(108,1,t[0])
            k.publish(t[0],k.held)
            a=sample(t[0]);out=c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            if pid is None:pid=c.pid
            self.assertIs(c.pid,pid)
            if i==100:
                self.assertAlmostEqual(a['position_velocity_target_m_s'],.03)
                self.assertAlmostEqual(a['velocity_hold']['target_velocity_m_s'],c.remote_v)
                self.assertGreater(c.remote_v,.08);self.assertLess(c.remote_v,.12)
            if i==280:self.assertGreaterEqual(c.remote_v,0.);self.assertLess(c.remote_v,.04)
            if i==400:
                self.assertAlmostEqual(a['position_velocity_target_m_s'],-.03)
                self.assertAlmostEqual(a['velocity_hold']['target_velocity_m_s'],c.remote_v)
                self.assertLess(c.remote_v,-.08);self.assertGreater(c.remote_v,-.12)
            for mid,sign in [(0,1),(1,-1)]:
                p=c.allocated_torque_packet(mid,sign,out[mid],PLAN);ff,rate,pos,kp,kd=struct.unpack_from('<hhihh',p,4)
                self.assertLessEqual(abs(ff*RATIO/256000.),.12+1e-12);self.assertLessEqual(abs(rate*math.tau/(RATIO*2.56)),6.)
                self.assertLessEqual(abs(c.native_allocations[mid].predicted_net_nm),.12+1e-12)
        # A stale input does not disarm or reset the body PID; it ramps intent to0.
        for i in range(501,1001):
            t[0]=i*.005;a=sample(t[0]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
        self.assertEqual(c.remote_v,0.);self.assertIs(c.pid,pid)
    def test_turn_sign_and_held_at_activation_requires_fresh_release(self):
        for code,sign in [(106,1),(105,-1)]:
            k=Keys();k.attach(0,[code]);t=[0.];c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
            for i in range(1,301):
                t[0]=i*.005
                if i==50:k.publish(t[0],[])
                if i==60:k.event(code,1,t[0])
                k.publish(t[0],k.held);a=sample(t[0]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
                if i==40:self.assertEqual(c.remote_turn,0.)
            self.assertEqual(c.remote_turn,sign*4.0)
            self.assertGreater(sign*a['wheel_sync']['position_term_nm'],0.)
    def test_drive_reference_preserves_gain_pitch_slew_and_rejects_oversized_target(self):
        t=[0.];k=Keys();k.attach(0,[]);c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
        previous=0.
        for i in range(1,160):
            t[0]=i*.005
            if i==2:k.event(103,1,t[0])
            k.publish(t[0],k.held);a=sample(t[0]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            ref=a['velocity_hold']['pitch_reference_deg']
            self.assertLessEqual(abs(ref-previous),PLAN['speed_pitch_reference_slew_dps']*.005+1e-10)
            self.assertLessEqual(abs(ref),PLAN['speed_pitch_reference_limit_deg'])
            previous=ref
        self.assertAlmostEqual(ref,math.degrees(.35*(c.remote_v-c.speed_reference.filtered_velocity)+c.speed_reference.remote_speed_integral_rad))
        r=RemoteVelocityReference();a=sample(1.);a['remote_velocity_target_m_s']=.121
        with self.assertRaisesRegex(Fault,'remote_velocity_target_outside_plan'):r(a,{0:0.,1:0.},PLAN)
    def test_remote_rate_target_and_release_share_the_existing_heading_reference(self):
        for code,sign in [(106,1),(105,-1)]:
            k=Keys();k.attach(0,[]);t=[0.];c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
            for i in range(1,281):
                t[0]=i*.005
                if i==20:k.event(code,1,t[0])
                if i==120:k.event(code,0,t[0])
                k.publish(t[0],k.held);a=sample(t[0]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
                sync=a['wheel_sync']
                self.assertLessEqual(abs(sync['correction_nm']),sync['available_margin_nm']+1e-12)
                if i==100:
                    self.assertAlmostEqual(sync['remote_rate_feedforward_nm'],c.remote_turn*.10)
                    self.assertGreater(sign*sync['correction_nm'],0.)
            self.assertEqual(c.remote_turn,0.)
            self.assertEqual(c.remote_expected_turn_rad,0.)
            self.assertEqual(c.heading_origin,c.remote_heading_start)
    def test_new_turn_does_not_fight_old_straight_heading_drift(self):
        k=Keys();k.attach(0,[]);t=[0.];c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
        for i in range(1,60):
            t[0]=i*.005;a=sample(t[0]);a['wheel_position_forward_rad'][0]=.1 if i>=20 else 0.
            if i==30:k.event(106,1,t[0])
            k.publish(t[0],k.held);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            if i==30:
                self.assertGreater(c.heading_origin,.1)
                self.assertAlmostEqual(c.remote_expected_turn_rad,c.heading_origin-c.remote_heading_start)
                self.assertGreater(a['wheel_sync']['correction_nm'],0.)
    def test_turn_rate_feedback_uses_both_target_and_measured_rate_with_pitch_priority(self):
        k=Keys();c=RemoteDriveController(TuningChannel(gains(PLAN)),k)
        for target in [4.0,-4.0,0.]:
            c.remote_turn=target
            for speeds in [{0:0.,1:0.},{0:.4,1:-.4},{0:-.4,1:.4}]:
                for common in [0.,.11,-.11,.12]:
                    a=sample(1.);c.heading_origin=0.;c.filtered_difference=0.
                    requests=c.net_torque_requests(common,speeds,a,PLAN)
                    self.assertAlmostEqual((requests[0]+requests[1])/2,common)
                    for value in requests.values():self.assertLessEqual(abs(value),.12+1e-12)
                    if target:
                        info=a['wheel_sync']
                        self.assertAlmostEqual(info['rate_term_nm'],.10*info['filtered_rate_difference_rad_s'])
                        self.assertLessEqual(abs(info['correction_nm']),.08+1e-12)
    def test_active_turn_brakes_overspeed_in_both_directions(self):
        for target in [4.0,-4.0]:
            c=RemoteDriveController(TuningChannel(gains(PLAN)),Keys())
            c.remote_turn=target;c.heading_origin=0.;c.filtered_difference=-2*target
            a=sample(1.);speeds={0:target,1:-target}
            requests=c.net_torque_requests(0.,speeds,a,PLAN)
            self.assertLess(target*(requests[0]-requests[1]),0.)
            self.assertAlmostEqual(requests[0]+requests[1],0.)
            self.assertLessEqual(max(abs(x) for x in requests.values()),.08+1e-12)
    def test_turn_commands_zero_mean_speed_and_captures_position_after_release(self):
        k=Keys();k.attach(0,[]);t=[0.];c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
        for i in range(1,441):
            t[0]=i*.005
            if i==2:c.position_origin=-.2;k.event(106,1,t[0])
            if i==180:k.event(106,0,t[0])
            k.publish(t[0],k.held);a=sample(t[0]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            if 2<=i<180:
                self.assertEqual(a['remote_velocity_target_m_s'],0.)
                self.assertAlmostEqual(a['velocity_hold']['target_velocity_m_s'],0.)
                self.assertAlmostEqual(a['position_hold']['relative_error_proxy_m'],0.)
            if i==160:self.assertEqual(c.remote_turn,4.0)
        self.assertEqual(c.remote_turn,0.);self.assertEqual(c.speed_reference.remote_speed_integral_rad,0.)
        self.assertAlmostEqual(c.position_origin,0.)
    def test_remote_speed_integral_bounded_symmetric_and_idle_reset(self):
        for sign in [1,-1]:
            r=RemoteVelocityReference();r.velocity_proxy=lambda a,s,p:0.;previous=0.
            for i in range(1,1001):
                a=sample(i*.005);a['remote_velocity_target_m_s']=sign*.08;r(a,{0:0.,1:0.},PLAN)
                ref=a['velocity_hold']['pitch_reference_deg']
                self.assertLessEqual(abs(ref-previous),PLAN['speed_pitch_reference_slew_dps']*.005+1e-9)
                self.assertLessEqual(abs(ref),3.);previous=ref
            self.assertAlmostEqual(r.remote_speed_integral_rad,sign*math.radians(.75))
            a=sample(5.005);r(a,{0:0.,1:0.},PLAN)
            self.assertEqual(r.remote_speed_integral_rad,0.)
    def test_remote_speed_integral_blocks_saturation_and_allows_unwinding(self):
        r=RemoteVelocityReference();r.velocity_proxy=lambda a,s,p:0.
        r.remote_speed_integral_rad=math.radians(.4)
        for i in range(1,21):
            a=sample(i*.005);a.update(remote_velocity_target_m_s=.12,remote_body_limited=True);r(a,{0:0.,1:0.},PLAN)
        self.assertAlmostEqual(r.remote_speed_integral_rad,math.radians(.4))
        for i in range(21,41):
            a=sample(i*.005);a.update(remote_velocity_target_m_s=-.12,remote_body_limited=True);r(a,{0:0.,1:0.},PLAN)
        self.assertLess(r.remote_speed_integral_rad,math.radians(.4))
    def test_turn_integral_bounded_unwinds_and_resets_without_changing_common(self):
        c=RemoteDriveController(TuningChannel(gains(PLAN)),Keys());c.remote_turn=.2
        for i in range(1,501):
            a=sample(i*.005);requests=c.net_torque_requests(0.,{0:0.,1:0.},a,PLAN)
            self.assertAlmostEqual(sum(requests.values()),0.)
        self.assertAlmostEqual(c.remote_turn_integral_nm,.02)
        for i in range(501,551):
            a=sample(i*.005);c.net_torque_requests(0.,{0:1.,1:-1.},a,PLAN)
        self.assertLess(c.remote_turn_integral_nm,.02)
        c.remote_turn=0.;a=sample(3.);c.net_torque_requests(0.,{0:0.,1:0.},a,PLAN)
        self.assertEqual(c.remote_turn_integral_nm,0.)
    def test_turn_integral_cannot_wind_up_while_pitch_consumes_budget(self):
        c=RemoteDriveController(TuningChannel(gains(PLAN)),Keys());c.remote_turn=4.0
        for i in range(1,301):
            a=sample(i*.005);requests=c.net_torque_requests(.12,{0:0.,1:0.},a,PLAN)
            self.assertEqual(c.remote_turn_integral_nm,0.)
            self.assertEqual(requests,{0:.12,1:.12})
    def test_release_brakes_before_capturing_actual_stopping_position(self):
        k=Keys();k.attach(0.,[]);t=[0.]
        c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
        speed=[0.];original_proxy=c.speed_reference.velocity_proxy
        c.speed_reference.velocity_proxy=lambda a,s,p:(original_proxy(a,s,p),speed[0])[1]
        position=0.;braking_frames=0;pid=None
        for i in range(1,1801):
            t[0]=i*.005
            if i==2:k.event(103,1,t[0])
            if i==802:k.event(103,0,t[0])
            k.publish(t[0],k.held)
            speed[0]=.04 if 3<=i<=1350 else 0.
            position+=speed[0]*.005
            a=sample(t[0]);a.update(pitch_deg=0.,pitch_error_deg=0.,pitch_rate_dps=0.)
            a['wheel_position_forward_rad']={0:position/.04,1:position/.04}
            speeds={0:speed[0]/.04,1:speed[0]/.04}
            c(a,speeds,PLAN);c.observe_pair(checked_pair(a))
            if pid is None:pid=c.pid
            self.assertIs(pid,c.pid)
            if 1230<=i<=1300:
                braking_frames+=1
                self.assertTrue(c.remote_stopping)
                self.assertEqual(a['remote_velocity_target_m_s'],0.)
                self.assertEqual(a['position_hold']['relative_error_proxy_m'],0.)
                self.assertEqual(a['velocity_hold']['target_velocity_m_s'],0.)
            if i==780:self.assertAlmostEqual(c.remote_v,.12,places=6)
        self.assertGreater(braking_frames,60)
        self.assertFalse(c.remote_stopping)
        self.assertAlmostEqual(c.position_origin,position)
        self.assertAlmostEqual(a['position_hold']['target_velocity_m_s'],0.)
        self.assertEqual(c.speed_reference.remote_speed_integral_rad,0.)

    def test_remote_stopping_bias_decays_without_pitch_reference_jump(self):
        r=RemoteVelocityReference();r.velocity_proxy=lambda a,s,p:0.
        r.remote_speed_integral_rad=math.radians(.75);previous=0.
        for i in range(1,201):
            a=sample(i*.005);a.update(remote_velocity_target_m_s=0.,remote_stopping=True)
            r(a,{0:0.,1:0.},PLAN);ref=a['velocity_hold']['pitch_reference_deg']
            self.assertLessEqual(abs(ref-previous),6*.005+1e-9);previous=ref
        self.assertLess(abs(r.remote_speed_integral_rad),math.radians(.006))

    def test_smooth_reference_short_taps_release_and_reverse_are_bounded(self):
        traces=[]
        for sign in [1,-1]:
            p=DriveVelocityProfile();values=[];prev=0.;peak_acc=0.
            for i in range(1,1001):
                target=sign*.12 if i<=40 else 0. #200ms short tap
                v=p.update(target,.005);values.append(v)
                peak_acc=max(peak_acc,abs(v-prev)/.005);prev=v
                self.assertGreaterEqual(sign*v,-1e-12)
                self.assertLessEqual(abs(v),.12+1e-12)
            self.assertLess(peak_acc,.23)
            self.assertEqual(values[-1],0.)
            self.assertLess(max(abs(x) for x in values),.045)
            traces.append(values)
        for a,b in zip(*traces):self.assertAlmostEqual(a,-b)
        p=DriveVelocityProfile()
        for _ in range(1000):p.update(.12,.005)
        self.assertAlmostEqual(p.velocity,.12,places=8)
        prev=p.velocity
        for _ in range(1000):
            v=p.update(-.12,.005);self.assertLessEqual(v,prev+1e-12)
            self.assertLessEqual(abs(v-prev),.30*.005+1e-12)
            self.assertLessEqual(abs(v),.12+1e-12);prev=v
        self.assertAlmostEqual(p.velocity,-.12,places=8)
        for target,dt in [(float('nan'),.005),(.121,.005),(0.,.026)]:
            with self.assertRaises(Fault):p.update(target,dt)

    def test_key_release_starts_trim_decay_before_velocity_reference_reaches_zero(self):
        k=Keys();k.attach(0.,[]);t=[0.]
        c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
        for i in range(1,501):
            t[0]=i*.005
            if i==2:k.event(103,1,t[0])
            if i==400:
                c.speed_reference.remote_speed_integral_rad=math.radians(.3)
                old_i=c.speed_reference.remote_speed_integral_rad
                k.event(103,0,t[0])
            k.publish(t[0],k.held);a=sample(t[0]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
            if 2<=i<=150:
                self.assertTrue(a['velocity_hold']['remote_speed_integral_held_for_transition'])
                self.assertEqual(c.speed_reference.remote_speed_integral_rad,0.)
            if i==400:
                self.assertTrue(a['remote_stopping'])
                self.assertGreater(c.remote_v,.1)
                self.assertAlmostEqual(c.speed_reference.remote_speed_integral_rad,old_i*math.exp(-.005/.20))

    def test_post_drive_position_tolerance_does_not_pull_back_small_offsets(self):
        for sign in [1,-1]:
            k=Keys();k.attach(0.,[]);t=[0.]
            c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
            c.remote_started=True;c.position_origin=0.
            for i,offset in enumerate([0.,.005,.015,.0199,.020,.0201,.04,.2],1):
                t[0]=i*.005;a=sample(t[0]);a['wheel_position_forward_rad']={0:sign*offset/.04,1:sign*offset/.04}
                k.publish(t[0],[]);c(a,{0:0.,1:0.},PLAN);c.observe_pair(checked_pair(a))
                expected=-sign*min(.03,.30*max(0.,offset-.020))
                self.assertAlmostEqual(a['velocity_hold']['target_velocity_m_s'],expected)
                self.assertEqual(c.position_origin,0.)
                self.assertAlmostEqual(a['position_hold']['relative_error_proxy_m'],sign*offset)
                self.assertEqual(a['position_hold']['post_drive_tolerance_m'],.020)
                self.assertAlmostEqual(a['remote_drive']['position_target_velocity_m_s'],expected)

    def test_tolerance_keeps_velocity_braking_and_upright_control_active(self):
        k=Keys();k.attach(0.,[]);t=[0.]
        c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
        c.remote_started=True;c.position_origin=0.
        original_proxy=c.speed_reference.velocity_proxy
        c.speed_reference.velocity_proxy=lambda a,s,p:(original_proxy(a,s,p),.04)[1]
        for i in range(1,40):
            t[0]=i*.005;a=sample(t[0]);a.update(pitch_deg=2.,pitch_error_deg=2.)
            a['wheel_position_forward_rad']={0:.01/.04,1:.01/.04}
            k.publish(t[0],[]);out=c(a,{0:1.,1:1.},PLAN);c.observe_pair(checked_pair(a))
            self.assertEqual(a['velocity_hold']['target_velocity_m_s'],0.)
            self.assertLess(a['velocity_hold']['pitch_reference_deg'],0.)
            self.assertGreater(abs(a['ardupilot_balance']['requested_net_nm']),1e-6)
        self.assertIsNotNone(c.pid)

    def test_original_position_return_retained_until_first_remote_action(self):
        k=Keys();k.attach(0.,[]);t=[.005]
        c=RemoteDriveController(TuningChannel(gains(PLAN),now=lambda:t[0]),k)
        c.position_origin=0.;a=sample(t[0]);a['wheel_position_forward_rad']={0:.015/.04,1:.015/.04}
        k.publish(t[0],[]);c(a,{0:0.,1:0.},PLAN)
        self.assertAlmostEqual(a['position_hold']['target_velocity_m_s'],-.0045)
        self.assertNotIn('post_drive_tolerance_m',a['position_hold'])

    def test_tracking_guard_allows_turn_and_unlimited_distance_but_preserves_error(self):
        class Intent:remote_expected_turn_rad=0.
        intent=Intent();rows={0:dict(position_rad=0.),1:dict(position_rad=0.)}
        tr=RemoteTravel(rows,{0:1,1:-1},PLAN,intent)
        for i in range(1,31):
            intent.remote_expected_turn_rad=i*.1
            for mid in (0,1):tr.update(mid,dict(position_rad=i*.05))
        self.assertAlmostEqual(tr.snapshot()['differential_tracking_error_m'],0.)
        with self.assertRaisesRegex(Fault,'turn_tracking'):tr.update(0,dict(position_rad=2.4))
        tr=RemoteTravel(rows,{0:1,1:-1},PLAN,Intent())
        #40m forward and40m back exceed both former limits; keep recording.
        for i in list(range(1,10001))+list(range(9999,-1,-1)):
            tr.update(0,dict(position_rad=i*.1));tr.update(1,dict(position_rad=-i*.1))
        self.assertAlmostEqual(tr.offset[0],0.)
        self.assertAlmostEqual(tr.path[0],80.,places=7)
        self.assertFalse(tr.snapshot()['distance_stops_enabled'])
        with self.assertRaisesRegex(Fault,'turn_tracking'):tr.update(0,dict(position_rad=1.))
    def test_distance_policy_explicit_and_invalid_encoder_still_rejected(self):
        class Intent:remote_expected_turn_rad=0.
        rows={0:dict(position_rad=0.),1:dict(position_rad=0.)}
        with self.assertRaisesRegex(Fault,'distance_policy'):
            RemoteTravel(rows,{0:1,1:-1},dict(PLAN,net_rolling_limit_m=.3),Intent())
        for bad in [float('nan'),float('inf')]:
            tr=RemoteTravel(rows,{0:1,1:-1},PLAN,Intent())
            with self.assertRaises(Fault):tr.update(0,dict(position_rad=bad))
    def test_finite_stop_and_feedback_failure_disable_both_no_remote_rearm(self):
        for fail in [False,True]:
            bus=Bus(timeout=True,fail=lambda m,p,phase:fail and m==1 and phase==PLAN['control_phase']);r={}
            c=RemoteDriveController(TuningChannel(gains(PLAN),now=bus.now),Keys())
            class Cue:
                def check(self):pass
                def tick(self):pass
                def deactivate(self):pass
            def exchange(mid):
                f=bus.exchange(mid)
                def call(p,phase):
                    row=f(p,phase);row['feedback_received_monotonic']=bus.now();return row
                return call
            factory=lambda rows,signs,plan:RemoteTravel(rows,signs,plan,c)
            run({m:exchange(m) for m in (0,1)},HandIMU(bus),copy.deepcopy(CAL),r,True,
                now=bus.now,sleep=bus.sleep,display=lambda _:None,plan=dict(PLAN,duration_s=.5),controller=c,travel_factory=factory,indicator=Cue())
            self.assertEqual(r['status'],'FAIL' if fail else 'PASS',r.get('reason'));self.assertTrue(r['final_disabled_verified'])
            stop=next(i for i,(_,_,phase) in enumerate(bus.log) if phase=='stop_transition')
            self.assertTrue(all(p[2]&0x70==0 for _,p,_ in bus.log[stop:]))
            with self.assertRaisesRegex(Fault,'cannot_reset'):c.reset()
if __name__=='__main__':unittest.main()
