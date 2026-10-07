import math,uuid,pytest
from simulation.device import Device
from simulation.vision import Vision,fixture,bearing
from contracts.protocol import SPEC
from simulation.harness import Clock,Rig

def test_stop_keeps_balance_disarm_requires_support():
 r=Rig();r.arm();r.issue('SET_VELOCITY',{'v_m_s':.1,'yaw_rad_s':0});r.tick(100)
 assert r.d.v>0;r.issue('STOP_MOTION');r.run(500)
 assert r.d.enabled and r.d.v==0 and r.d.state=='ARMED_IDLE'
 assert r.issue('DISARM',{'support_confirmed':False})['status']=='REJECTED'
 r.issue('DISARM',{'support_confirmed':True});assert not r.d.enabled

def test_timeout_disconnect_no_rearm_and_reboot_session():
 r=Rig();r.arm();old=r.cmd('SET_VELOCITY',{'v_m_s':.1,'yaw_rad_s':0});r.d.issue(old,r.p)
 r.d.disconnect('a');r.tick();assert r.d.target_v==0 and r.d.enabled and r.d.owner is None
 r.d.reset();assert r.d.issue(old,r.p)['reason']=='SESSION';assert not r.d.enabled

def test_duplicate_expiry_sequence_and_two_clients():
 r=Rig();r.arm();c=r.cmd('HEARTBEAT');r.d.issue(c,r.p);end=r.d.lease_end;r.tick(200);r.d.issue(c,r.p);assert r.d.lease_end==end
 assert r.issue('CLAIM_CONTROL',{'supervised':True},client='b')['reason']=='CONTROL_OWNED'
 assert r.issue('HEAD_TARGET',{'yaw_rad':0,'pitch_rad':0},sequence=1)['reason']=='OUT_OF_ORDER'
 assert r.issue('SET_EXPRESSION',{'state':'idle'},basis_device_ms=r.clock()-301)['status']=='EXPIRED'
 assert r.issue('STOP_MOTION',sequence=1)['status']=='COMPLETED'

def test_cached_result_cannot_be_overwritten_by_wrong_session():
 r=Rig();r.arm();c=r.cmd('READ_STATUS');result=r.d.issue(c,r.p)
 r.d.issue(dict(c,session_id='wrong'),r.p)
 assert r.d.issue(c,r.p)==result

@pytest.mark.parametrize('attr,value',[('imu_ok',False),('encoder_ok',False),('supply_ok',False),('body_pitch',.5)])
def test_fault_latched_manual_ack(attr,value):
 r=Rig();r.arm();setattr(r.d,attr,value);r.tick();assert r.d.state=='FAULT' and not r.d.enabled
 setattr(r.d,attr,0 if attr=='body_pitch' else True);r.tick();assert r.d.state=='FAULT'
 r.issue('CLAIM_CONTROL',{'supervised':True});assert r.issue('ARM',{'local_confirmation':True})['status']=='REJECTED'
 assert r.issue('ACK_FAULT',{'support_confirmed':False})['status']=='REJECTED'
 r.issue('ACK_FAULT',{'support_confirmed':True});assert r.d.state=='DISARMED' and not r.d.enabled

def test_low_voltage_head_inhibition_and_visual_sleep():
 r=Rig();r.arm();r.issue('SET_EXPRESSION',{'state':'sleep_visual'});assert r.d.enabled
 r.issue('HEAD_TARGET',{'yaw_rad':.5,'pitch_rad':.2});r.tick();r.d.low_battery=True;r.tick();assert r.d.enabled and r.d.target_v==0 and r.d.head_inhibited

def test_finite_distance_patrol_and_cancel():
 r=Rig();r.arm();c=r.issue('MOVE_DISTANCE',{'distance_m':.1});r.run(2500)
 assert r.d.results[c['command_id']]['status']=='COMPLETED';assert .1<=r.d.distance<.13
 c=r.issue('PATROL',{'duration_s':1,'segment_m':.1,'supervised':True});r.run(1100);assert r.d.results[c['command_id']]['status']=='COMPLETED';assert r.d.enabled
 c=r.issue('ACTIVE_ACTION',{'pattern':'short_forward','supervised':True});r.issue('CANCEL',{'command_id':c['command_id']});assert r.d.results[c['command_id']]['status']=='CANCELLED'

def test_head_limits_trajectory_and_button():
 r=Rig();r.issue('CLAIM_CONTROL',{'supervised':True});r.issue('HEAD_TARGET',{'yaw_rad':1,'pitch_rad':.4})
 last=r.d.head[:]
 for _ in range(300):
  r.issue('HEARTBEAT');r.tick();assert max(abs(r.d.head[j]-last[j]) for j in range(2))<=.005201;last=r.d.head[:]
 assert abs(r.d.head[0]-1)<.003
 assert r.issue('BUTTON',{'gesture':'long'})['status']=='REJECTED'
 r.issue('BUTTON',{'gesture':'double'});assert r.d.target_v==0

def test_head_camera_transform_and_pixel_loss():
 assert bearing([.5,.5],[.4,.2],0)==pytest.approx([.4,.2])
 assert bearing([.8,.5],[0,0],0)[0]<0
 v=Vision();assert not v.detect(fixture(1))['uncertain']
 assert v.detect(fixture(2,'multiple'))['uncertain'];assert v.detect(fixture(3,'dark'))['uncertain']
 r=Rig();r.arm();r.issue('CAMERA_MODE',{'mode':'TRACKING','upload_allowed':False});f=r.d.capture();r.d.observe(f,Vision().detect(fixture(1)));r.issue('SELECT_TARGET',{'target_id':'track-1','confirmed':True});r.issue('FOLLOW',{'mode':'BODY','supervised':True});r.tick();assert r.d.active
 r.run(260);assert r.d.active is None and r.d.target_v==0 and r.d.selected_target is None and r.d.enabled
 assert not r.d.observe(f,Vision().detect(fixture(1)))

def test_conversation_and_button_stop_do_not_depend_on_motion_lease():
 r=Rig();assert r.issue('VOICE_SESSION',{'action':'start','text':''})['status']=='COMPLETED'
 assert r.issue('BUTTON',{'gesture':'double'})['status']=='COMPLETED'
 assert r.issue('SET_VELOCITY',{'v_m_s':.1,'yaw_rad_s':0})['status']=='REJECTED'
 assert not r.d.enabled


def test_capture_to_current_body_coordinates_and_odometry_limit():
 from simulation.vision import target_angles
 assert target_angles([.5,.5],[.4,.2],.1,0,.1,0)==pytest.approx([.4,.2])
 assert target_angles([.5,.5],[.4,0],0,.2,0,.3)==pytest.approx([.3,0])
 assert target_angles([.5,.5],[0,.2],.1,0,.15,0)==pytest.approx([0,.25])
 r=Rig();r.arm();r.d.distance=10
 c=r.issue('PATROL',{'duration_s':1,'segment_m':.1,'supervised':True});r.tick();assert r.d.results[c['command_id']]['status']=='RUNNING'

def test_active_action_result_survives_telemetry_command_history():
 r=Rig();r.arm();c=r.issue('PATROL',{'duration_s':20,'segment_m':.1,'supervised':True})
 for _ in range(520):r.issue('HEARTBEAT')
 assert r.d.results[c['command_id']]['status']=='RUNNING'
 assert len(r.d.results)<=512

def test_leaving_tracking_freezes_head_instead_of_finishing_stale_follow_target():
 r=Rig();r.arm();r.issue('CAMERA_MODE',{'mode':'TRACKING','upload_allowed':False})
 f=r.d.capture();r.d.observe(f,Vision().detect(fixture(1)))
 r.issue('SELECT_TARGET',{'target_id':'track-1','confirmed':True})
 assert r.issue('FOLLOW',{'mode':'HEAD','supervised':True})['status']=='RUNNING'
 r.d.head_target=[.5,.2];r.d.head_velocity=[.1,.1]
 r.issue('CAMERA_MODE',{'mode':'OFF','upload_allowed':False})
 assert r.d.active is None and r.d.head_target==r.d.head and r.d.head_velocity==[0.,0.]
