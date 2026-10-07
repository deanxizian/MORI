"""Local command/lease executor with injectable monotonic time. Kinematic simulation.
Physical balance is supplied only by a separately verified motion MCU adapter.
"""
import math,uuid
from collections import OrderedDict,deque
from contracts.protocol import SPEC,validate,ProtocolError
from contracts.profile import PROFILE, unavailable_sensors

def approach(v,target,delta):return max(v-delta,min(v+delta,target))
class Device:
 def __init__(self,clock,hardware=False):
  self.clock=clock;self.hardware=hardware;self.device_id='mori-sim-01' if not hardware else 'mori-hardware-pending'
  self.reset()
 def reset(self):
  self.session=uuid.uuid4().hex;self.state='DISARMED';self.enabled=False;self.fault=None
  self.owner=None;self.lease_end=0;self.last_sequence={};self.results=OrderedDict();self.events=deque(maxlen=256);self.head_command=None
  self.active=None;self.v=self.w=self.target_v=self.target_w=0.;self.x=self.y=self.heading=self.distance=0.
  self.head=[0.,0.];self.head_velocity=[0.,0.];self.head_target=[0.,0.]
  self.expression='idle';self.camera='OFF';self.upload_allowed=False;self.selected_target=None
  self.observation=None;self.frame_registry={};self.camera_frame=0;self.camera_age_ms=None
  self.supervised=False;self.supported=False;self.cabled=False;self.imu_ok=True;self.encoder_ok=True
  self.body_pitch=0.;self.supply_ok=True;self.low_battery=False;self.self_test_ok=True
  self.last_tick=self.clock();self.telemetry_sequence=0;self.volume=.55;self.voice='idle'
  self.wake_enabled=False;self.requested_wake='你好，莫里';self.wake_status='BLOCKED_MODEL_NOT_PROVIDED'
  self.head_inhibited=False;self.head_feedback_ok=True;self.transition('BOOT');self.transition('SELF_TEST');self.transition('DISARMED')
 def transition(self,state):
  self.state=state;self.events.append({'kind':'state','state':state,'device_ms':self.clock(),'source':'HARDWARE' if self.hardware else 'SIMULATION'})
 def result(self,c,status,reason='',data=None):
  value={'command_id':c['command_id'],'client_id':c.get('client_id',self.results.get(c['command_id'],{}).get('client_id')),'type':c['type'],'status':status,'reason':reason,'device_ms':self.clock(),'data':data}
  self.results[c['command_id']]=value;self.results.move_to_end(c['command_id'])
  while len(self.results)>512:
   terminal=next((key for key,item in self.results.items() if item['status'] not in ('RUNNING','ACCEPTED')),None)
   if terminal is None:raise RuntimeError('ACTIVE_RESULT_CAPACITY')
   del self.results[terminal]
  self.events.append({'kind':'command',**{k:v for k,v in value.items() if k!='data'}});return value
 def cancel(self,reason,status='CANCELLED'):
  if self.active:self.result(self.active['command'],status,reason)
  self.active=None;self.target_v=self.target_w=0
 def cancel_head(self,reason):
  if self.head_command:self.result(self.head_command,'CANCELLED',reason)
  self.head_command=None;self.head_target=self.head[:];self.head_velocity=[0.,0.]
 def fault_stop(self,reason):
  self.cancel(reason,'FAULT');self.fault=self.fault or reason;self.enabled=False;self.owner=None
  self.cancel_head(reason)
  if self.state!='FAULT':self.transition('FAULT')
 def healthy(self):return self.imu_ok and self.encoder_ok and self.supply_ok and abs(self.body_pitch)<math.radians(20)
 def disconnect(self,client):
  if self.owner==client:self.lease_end=min(self.lease_end,self.clock())
 def issue(self,c,principal):
  try:validate(c)
  except (ProtocolError,TypeError,ValueError):return {'command_id':c.get('command_id','INVALID'),'status':'REJECTED','reason':'PROTOCOL'}
  now=self.clock();kind=c['type'];p=c['params'];client=c['client_id'];rule=SPEC['commands'][kind]
  if client!=principal['client_id'] or not set(c['permissions'])<=set(principal['permissions']) or rule['permission'] not in principal['permissions']:return {'command_id':c['command_id'],'status':'REJECTED','reason':'AUTHORIZATION'}
  if c['device_id']!=self.device_id or c['session_id']!=self.session:return {'command_id':c['command_id'],'status':'REJECTED','reason':'SESSION'}
  if c['command_id'] in self.results:
   previous=self.results[c['command_id']]
   return previous if previous.get('client_id')==client else {'command_id':c['command_id'],'status':'REJECTED','reason':'ID_COLLISION'} # retry never renews a lease
  if c['sequence']<=self.last_sequence.get(client,0) and kind not in ('STOP_MOTION','FAULT_STOP'):return self.result(c,'REJECTED','OUT_OF_ORDER')
  self.last_sequence[client]=max(c['sequence'],self.last_sequence.get(client,0))
  age=now-c['basis_device_ms']
  if age<0 or age>=c['valid_for_ms']:return self.result(c,'EXPIRED','DEVICE_BASIS_STALE')
  if kind=='READ_STATUS':return self.result(c,'COMPLETED',data=self.snapshot())
  if kind=='FAULT_STOP':self.fault_stop(p['reason']);return self.result(c,'FAULT',self.fault)
  if kind=='STOP_MOTION':
   self.cancel('STOP_MOTION');self.selected_target=None
   if self.enabled:self.transition('ARMED_IDLE')
   return self.result(c,'COMPLETED')
  if kind=='CLAIM_CONTROL':
   if self.owner and self.owner!=client and now<self.lease_end:return self.result(c,'REJECTED','CONTROL_OWNED')
   if not p['supervised']:return self.result(c,'REJECTED','SUPERVISION_REQUIRED')
   self.cancel('CONTROL_CHANGE');self.owner=client;self.supervised=True;self.lease_end=c['basis_device_ms']+min(c['valid_for_ms'],300)
   return self.result(c,'COMPLETED')
  # Motion requires the local lease. Authorized interaction remains independent of
  # motion; audio/browser startup latency must never extend or recreate a lease.
  independent=kind in ('SET_EXPRESSION','VOLUME','VOICE_SESSION','CAMERA_MODE','SNAPSHOT','WAKE_CONFIG','BUTTON')
  if not independent and (self.owner!=client or now>=self.lease_end):return self.result(c,'REJECTED','NO_LEASE')
  if kind=='HEARTBEAT':self.lease_end=c['basis_device_ms']+min(c['valid_for_ms'],300);return self.result(c,'COMPLETED')
  if kind=='RELEASE_CONTROL':self.cancel('LEASE_RELEASED');self.owner=None;return self.result(c,'COMPLETED')
  if kind=='ACK_FAULT':
   if not p['support_confirmed'] or not self.healthy():return self.result(c,'REJECTED','SUPPORT_OR_HEALTH')
   self.fault=None;self.enabled=False;self.transition('DISARMED');return self.result(c,'COMPLETED')
  if kind=='DISARM':
   if not p['support_confirmed']:return self.result(c,'REJECTED','SUPPORT_REQUIRED')
   self.cancel('DISARM');self.enabled=False
   if self.state!='FAULT':self.transition('DISARMED')
   return self.result(c,'COMPLETED')
  if kind=='ENTER_MAINTENANCE':
   if not p['support_confirmed'] or self.enabled:return self.result(c,'REJECTED','DISARM_AND_SUPPORT_REQUIRED')
   self.supported=True;self.cabled=p['cabled'];self.transition('DOCKED_MAINTENANCE');return self.result(c,'COMPLETED','HUMAN_CONFIRMATION_ONLY')
  if kind=='MAINTENANCE_ACTION':
   if self.state!='DOCKED_MAINTENANCE' or not self.supported:return self.result(c,'REJECTED','MAINTENANCE_REQUIRED')
   if self.hardware:return self.result(c,'REJECTED','HARDWARE_ADAPTER_NOT_VERIFIED')
   return self.result(c,'COMPLETED','SIMULATED_MAINTENANCE_NO_FLASH_NO_NVS')
  if kind=='ARM':
   if self.hardware:return self.result(c,'REJECTED','PHYSICAL_GATES_NOT_VERIFIED')
   if self.fault or not self.healthy() or self.low_battery or self.cabled or self.state!='DISARMED' or not p['local_confirmation']:return self.result(c,'REJECTED','ARM_PRECONDITION')
   self.supported=False;self.enabled=True;self.transition('ARMED_IDLE');return self.result(c,'COMPLETED','SIMULATION_ONLY')
  if kind=='CANCEL':
   if self.active and self.active['command']['command_id']==p['command_id']:self.cancel('USER_CANCEL');return self.result(c,'COMPLETED')
   return self.result(c,'REJECTED','NO_MATCHING_ACTION')
  if kind=='SET_EXPRESSION':self.expression=p['state'];return self.result(c,'COMPLETED')
  if kind=='VOLUME':self.volume=p['level'];return self.result(c,'COMPLETED')
  if kind=='CAMERA_MODE':
   self.camera=p['mode'];self.upload_allowed=p['upload_allowed'];self.observation=None;self.selected_target=None
   if self.active and self.active['mode']=='FOLLOW':self.cancel('CAMERA_MODE_CHANGED')
   return self.result(c,'COMPLETED','SIMULATED_INPUT' if not self.hardware else 'CAMERA_DRIVER_PENDING')
  if kind=='SNAPSHOT':
   if self.camera!='SNAPSHOT':return self.result(c,'REJECTED','SNAPSHOT_MODE_REQUIRED')
   return self.result(c,'COMPLETED','UPLOAD_CONSENT_REQUIRED' if p['upload_allowed'] else 'LOCAL_ONLY')
  if kind=='SELECT_TARGET':
   if self.camera!='TRACKING' or not p['confirmed'] or not self.observation or self.observation['uncertain'] or self.observation['target_id']!=p['target_id']:return self.result(c,'REJECTED','TARGET_NOT_CONFIRMED')
   self.selected_target=p['target_id'];return self.result(c,'COMPLETED')
  if kind=='WAKE_CONFIG':
   self.wake_enabled=False;self.requested_wake=p['requested_phrase'];return self.result(c,'REJECTED','CUSTOM_MODEL_NOT_PROVIDED')
  if kind=='VOICE_SESSION':
   self.voice='idle' if p['action']=='interrupt' else 'listening';self.expression='idle' if self.voice=='idle' else 'listening'
   if p['text'].strip() in ('停下','停止移动'):
    self.cancel('VOICE_STOP_MOTION')
   return self.result(c,'COMPLETED','MOCK_VOICE' if not self.hardware else 'VOICE_HARDWARE_PENDING')
  if kind=='BUTTON':
   if p['gesture']=='double':self.cancel('BUTTON_DOUBLE');self.selected_target=None
   elif p['gesture']=='short':self.voice='idle' if self.voice!='idle' else 'listening';self.expression=self.voice
   elif self.state!='DOCKED_MAINTENANCE':return self.result(c,'REJECTED','MAINTENANCE_REQUIRED')
   return self.result(c,'COMPLETED','SIMULATED_BUTTON')
  if self.fault or not self.healthy():return self.result(c,'REJECTED','FAULT_OR_HEALTH')
  if kind=='HEAD_TARGET':
   if self.hardware or self.low_battery or abs(self.body_pitch)>math.radians(10):return self.result(c,'REJECTED','HEAD_INHIBITED_OR_UNVERIFIED')
   if self.head_command:self.result(self.head_command,'CANCELLED','HEAD_SUPERSEDED')
   self.head_command=c;self.head_target=[p['yaw_rad'],p['pitch_rad']];self.result(c,'ACCEPTED','HEAD_ESTIMATED');return self.result(c,'RUNNING','HEAD_ESTIMATED')
  head_only=kind=='FOLLOW' and p.get('mode')=='HEAD' or kind=='ACTIVE_ACTION' and p.get('pattern') in ('nod','shake')
  if self.hardware or (not self.enabled and not head_only) or self.cabled and not head_only or self.low_battery:return self.result(c,'REJECTED','MOTION_GATE')
  if kind in ('FOLLOW','PATROL','ACTIVE_ACTION') and (not self.supervised or not p['supervised']):return self.result(c,'REJECTED','SUPERVISION_REQUIRED')
  if kind=='FOLLOW' and (self.camera!='TRACKING' or not self.selected_target):return self.result(c,'REJECTED','SELECT_TARGET_FIRST')
  self.cancel('SUPERSEDED')
  if kind in ('FOLLOW','ACTIVE_ACTION'):self.cancel_head('AUTONOMY_SUPERSEDED')
  self.result(c,'ACCEPTED')
  self.active={'command':c,'mode':kind,'started':now,'distance_start':self.distance,'heading_start':self.heading,'total_start':self.distance,'phase':0,'end':now+30000}
  if kind=='SET_VELOCITY':self.target_v=p['v_m_s'];self.target_w=p['yaw_rad_s'];self.active['end']=c['basis_device_ms']+c['valid_for_ms']
  elif kind=='MOVE_DISTANCE':self.target_v=math.copysign(.06,p['distance_m']) if p['distance_m'] else 0
  elif kind=='TURN_ANGLE':self.target_w=math.copysign(.25,p['angle_rad']) if p['angle_rad'] else 0
  elif kind=='PATROL':self.active['end']=now+p['duration_s']*1000
  if not head_only:self.transition('AUTONOMY' if kind in ('FOLLOW','PATROL','ACTIVE_ACTION') else 'MOVING')
  return self.result(c,'RUNNING')
 def capture(self):
  self.camera_frame+=1;frame=self.camera_frame;self.frame_registry[frame]={'captured_ms':self.clock(),'head':self.head[:],'body_pitch':self.body_pitch,'body_yaw':self.heading}
  if len(self.frame_registry)>16:del self.frame_registry[min(self.frame_registry)]
  return frame
 def observe(self,frame,result):
  capture=self.frame_registry.get(frame)
  if not capture or self.clock()-capture['captured_ms']>250 or not self.head_feedback_ok:return False
  if self.observation and frame<=self.observation['frame_id']:return False
  self.observation={**result,**capture,'frame_id':frame,'processed_ms':self.clock()};return True
 def tick(self):
  now=self.clock();dt=min(.05,max(0,(now-self.last_tick)/1000));self.last_tick=now
  if not self.healthy():self.fault_stop('IMU' if not self.imu_ok else 'ENCODER' if not self.encoder_ok else 'POWER' if not self.supply_ok else 'SEVERE_TILT')
  if self.owner and now>=self.lease_end:self.cancel('LEASE_EXPIRED','EXPIRED');self.cancel_head('LEASE_EXPIRED');self.owner=None;self.selected_target=None
  if self.low_battery:self.cancel('LOW_BATTERY_SUPPORT_REQUEST')
  self.head_inhibited=self.low_battery or abs(self.body_pitch)>math.radians(10) or self.fault is not None
  if self.head_inhibited:self.head_target=self.head[:];self.head_velocity=[0.,0.]
  if self.active:
   a=self.active;p=a['command']['params'];mode=a['mode'];done=False
   if now>=a['end']:self.cancel('ACTION_TIME_LIMIT','EXPIRED' if mode=='SET_VELOCITY' else 'COMPLETED')
   elif mode=='MOVE_DISTANCE':done=abs(self.distance-a['distance_start'])>=abs(p['distance_m'])
   elif mode=='TURN_ANGLE':done=abs(self.heading-a['heading_start'])>=abs(p['angle_rad'])
   elif mode=='PATROL':
    if a['phase']%2==0:
     self.target_v=.05;self.target_w=0
     if abs(self.distance-a['distance_start'])>=p['segment_m']:a['phase']+=1;a['heading_start']=self.heading
    else:
     self.target_v=0;self.target_w=.25
     if abs(self.heading-a['heading_start'])>=math.pi/2:a['phase']+=1;a['distance_start']=self.distance
    if self.distance-a.get('total_start',0)>1.2:done=True
   elif mode=='ACTIVE_ACTION':
    elapsed=(now-a['started'])/1000
    if p['pattern']=='short_forward':self.target_v=.04;done=abs(self.distance-a['distance_start'])>=.10
    else:
     axis=1 if p['pattern']=='nod' else 0;self.head_target[axis]=.12*math.sin(elapsed*3.14159);done=elapsed>=2
   elif mode=='FOLLOW':
    obs=self.observation;age=now-obs['captured_ms'] if obs else 100000
    self.camera_age_ms=age
    if not self.head_feedback_ok or not obs or age>250 or obs['uncertain'] or obs['confidence']<.9 or obs['target_id']!=self.selected_target:
     self.cancel('TARGET_LOST_OR_STALE');self.selected_target=None
    else:
     from simulation.vision import target_angles
     yaw,pitch=target_angles(obs['center'],obs['head'],obs['body_pitch'],obs['body_yaw'],self.body_pitch,self.heading)
     self.head_target=[max(-math.pi/3,min(math.pi/3,yaw)),max(-math.pi/9,min(math.pi*25/180,pitch))]
     if p['mode']=='BODY':
      self.target_w=max(-.3,min(.3,yaw*.5));self.target_v=.04 if .08<obs['height_fraction']<.20 and abs(yaw)<.3 else 0
      if obs['height_fraction']>.65:self.cancel('RELATIVE_NEAR_LIMIT')
   if done and self.active:self.cancel('TARGET_REACHED','COMPLETED')
  if not self.active and self.enabled:self.transition('ARMED_IDLE') if self.state!='ARMED_IDLE' else None
  # Intentional kinematic simulation: no assertion of physical balance/torque/current.
  self.v=approach(self.v,self.target_v if self.enabled else 0,.2*dt);self.w=approach(self.w,self.target_w if self.enabled else 0,1*dt)
  self.heading+=self.w*dt;ds=self.v*dt;self.distance+=abs(ds);self.x+=ds*math.cos(self.heading);self.y+=ds*math.sin(self.heading)
  for j in range(2):
   error=self.head_target[j]-self.head[j];desired=math.copysign(min(.52,math.sqrt(2*1.05*abs(error))),error) if error else 0
   self.head_velocity[j]=approach(self.head_velocity[j],desired,1.05*dt)
   step=self.head_velocity[j]*dt
   if abs(step)>=abs(error):self.head[j]=self.head_target[j];self.head_velocity[j]=0
   else:self.head[j]+=step
  if self.head_command:
   if self.head_inhibited:self.result(self.head_command,'CANCELLED','HEAD_INHIBITED');self.head_command=None
   elif max(abs(self.head[j]-self.head_target[j]) for j in range(2))<.002:
    self.result(self.head_command,'COMPLETED','ESTIMATED_ONLY');self.head_command=None
  self.telemetry_sequence+=1
 def snapshot(self):
  now=self.clock()
  return {'protocol':'MORI/2','software_version':PROFILE['software_version'],'parameter_version':PROFILE['parameter_version'],'hardware_profile':'STM32F413 / S288 / SCS0009 / CAM-OV3660 / ST77916','physical_release':False,'sensors':unavailable_sensors(),'device_id':self.device_id,'session_id':self.session,'source':'HARDWARE' if self.hardware else 'SIMULATED','device_ms':now,'frame_id':self.telemetry_sequence,'state':self.state,'enabled':self.enabled,'fault':self.fault,'owner':self.owner,'lease_remaining_ms':max(0,self.lease_end-now) if self.owner else 0,'v_m_s':self.v,'yaw_rad_s':self.w,'target_v_m_s':self.target_v,'pose':{'x_m':self.x,'y_m':self.y,'yaw_rad':self.heading,'frame':'control'},'head':{'yaw_rad':self.head[0],'pitch_rad':self.head[1],'feedback':'ESTIMATED','inhibited':self.head_inhibited},'expression':self.expression,'camera':{'mode':self.camera,'upload_allowed':self.upload_allowed,'selected_target':self.selected_target,'observation':self.observation,'age_ms':now-self.observation['captured_ms'] if self.observation else None},'voice':self.voice,'volume':self.volume,'wake':{'enabled':self.wake_enabled,'phrase':self.requested_wake,'status':self.wake_status},'active':self.active['command']['command_id'] if self.active else None,'measurements':{'battery_v':None,'current_a':None,'temperature_c':None,'hardware_timing_max_us':None},'capabilities':{'simulation':not self.hardware,'physical_motion':'BLOCKED','physical_head_pitch':'BLOCKED','camera_input':'SIMULATED_PIXELS' if not self.hardware else 'BLOCKED','physical_autonomy':'BLOCKED','custom_wake_word':'BLOCKED'},'events':list(self.events)[-30:]}
