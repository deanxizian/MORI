import asyncio,base64,contextlib,json,os,pathlib,time,io,wave,math
from contextlib import asynccontextmanager
import cv2
from fastapi import FastAPI,HTTPException,Request,WebSocket,WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from contracts.protocol import parse,validate,ProtocolError,SPEC
from contracts.profile import PROFILE
from simulation.device import Device
from simulation.vision import Vision,fixture
from .auth import Auth
from .memory import Memory
from .providers import MockServices,TencentServices,Budget
from .inputs import object_json

class Gateway:
 def __init__(self,directory,clock=None):
  self.clock=clock or (lambda:int(time.monotonic()*1000));self.device=Device(self.clock)
  self.auth=Auth(directory);self.memory=Memory(pathlib.Path(directory)/'memory.sqlite')
  self.budget=Budget(int(os.environ['MORI_API_CALL_LIMIT']) if os.environ.get('MORI_API_CALL_LIMIT') else None,pathlib.Path(directory)/'api-budget.sqlite')
  self.services=TencentServices(self.budget) if os.environ.get('MORI_PROVIDER')=='tencent' else MockServices()
  self.vision=Vision();self.frame_jpeg=None;self.last_frame_ms=0;self.scenario='single';self.voice_tasks={};self.sockets={};self.voice_metrics={}
 async def tick(self):
  self.device.tick();now=self.clock()
  for ident,m in list(self.voice_metrics.items()):
   result=self.device.results.get(ident,{})
   if result.get('status')=='RUNNING' and now-m['requested_ms']>=90000:
    self.device.result(result,'EXPIRED','VOICE_PLAYBACK_TIMEOUT');m['interrupt_requested_ms']=now
    task=self.voice_tasks.pop(result['client_id'],None)
    if task and not task.done():task.cancel()
    await self.send(result['client_id'],{'type':'voice_interrupt','command_ids':[ident]})
   if len(self.voice_metrics)>256 and result.get('status')!='RUNNING':self.voice_metrics.pop(ident,None)
  if self.device.camera=='TRACKING' and now-self.last_frame_ms>=100:
   self.last_frame_ms=now;frame=self.device.capture();image=fixture(frame,self.scenario)
   result=self.vision.detect(image);self.device.observe(frame,result)
   self.frame_jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,55])[1].tobytes()
  if self.device.camera=='OFF':self.frame_jpeg=None
 async def dispatch(self,c,p):
  validate(c)
  kind=c['type'];params=c['params'];d=self.device
  reject=lambda reason:{'command_id':c['command_id'],'status':'REJECTED','reason':reason}
  if kind.startswith('MEMORY_'):
   if c['client_id']!=p['client_id'] or 'memory' not in p['permissions'] or not set(c['permissions'])<=set(p['permissions']):return reject('AUTHORIZATION')
   if c['device_id']!=d.device_id or c['session_id']!=d.session:return reject('SESSION')
   if c['command_id'] in d.results:
    old=d.results[c['command_id']]
    return old if old['client_id']==p['client_id'] else reject('ID_COLLISION')
   if c['sequence']<=d.last_sequence.get(p['client_id'],0):return d.result(c,'REJECTED','OUT_OF_ORDER')
   d.last_sequence[p['client_id']]=c['sequence']
   if not 0<=self.clock()-c['basis_device_ms']<c['valid_for_ms']:return d.result(c,'EXPIRED','DEVICE_BASIS_STALE')
   try:
    u=p['user_id'];dev=d.device_id;data=None
    if kind=='MEMORY_QUERY':data=self.memory.query(u,dev,params['query'])
    elif kind=='MEMORY_REMEMBER':data={'id':self.memory.remember(u,dev,**params)}
    elif kind=='MEMORY_CORRECT':self.memory.correct(u,dev,params['id'],params['text'],params['source_id'],params['confirmed'])
    elif kind=='MEMORY_DELETE':
     self.memory.delete(u,dev,params['id'])
     for old in d.results.values():
      if old['type'].startswith('MEMORY_'):old['data']=None
    elif kind=='MEMORY_EXPORT':data=self.memory.export(u,dev)
    elif kind=='MEMORY_ENABLED':self.memory.set_enabled(u,dev,params['enabled'])
    return d.result(c,'COMPLETED',data=data)
   except ValueError as e:return d.result(c,'REJECTED',str(e))
  cached=c['command_id'] in d.results
  result=d.issue(c,p)
  if cached:return result
  if result['status'] not in ['REJECTED','EXPIRED','FAULT'] and kind=='VOICE_SESSION':
   client=p['client_id']
   if params['action'] in ('interrupt','text'):
    interrupted=[]
    for ident,m in self.voice_metrics.items():
     previous=d.results.get(ident,{})
     if previous.get('client_id')==client and previous.get('status')=='RUNNING':
      m['interrupt_requested_ms']=self.clock();d.result(previous,'CANCELLED','VOICE_INTERRUPTED');interrupted.append(ident)
    await self.send(client,{'type':'voice_interrupt','command_ids':interrupted})
   if params['action']=='interrupt':
    task=self.voice_tasks.pop(client,None)
    if task:task.cancel()
   elif params['action']=='text':
    task=self.voice_tasks.pop(client,None)
    if task:task.cancel()
    self.voice_tasks[client]=asyncio.create_task(self.conversation(c,p))
    return d.result(c,'RUNNING','WAITING_FOR_PLAYBACK')
  return result
 async def send(self,client,data):
  ws=self.sockets.get(client)
  if ws:
   with contextlib.suppress(Exception):await ws.send_json(data)
 async def conversation(self,c,p):
  ident=c['command_id'];start=self.clock();m={'source':self.services.source,'playback_source':'HOST_WEB_AUDIO','timebase':'GATEWAY_MONOTONIC_MS','requested_ms':start,'first_text_ms':None,'first_audio_generated_ms':None,'playback_start_received_ms':None,'playback_end_received_ms':None,'interrupt_requested_ms':None,'generation_cancelled_ms':None,'interrupt_complete_ms':None,'position_ms':0}
  self.voice_metrics[ident]=m
  try:
   self.device.expression='thinking'
   memories=self.memory.query(p['user_id'],self.device.device_id,c['params']['text'][:64])
   text=await self.services.llm(c['params']['text'],memories);m['first_text_ms']=self.clock()
   audio=await self.services.tts(text);m['first_audio_generated_ms']=self.clock()
   await self.send(p['client_id'],{'type':'voice_audio','command_id':ident,'text':text,'source':self.services.source,'audio_base64':base64.b64encode(audio).decode(),'format':'wav','half_duplex':True,'metrics':m})
  except asyncio.CancelledError:
   m['generation_cancelled_ms']=self.clock()
   if self.device.results.get(ident,{}).get('status')=='RUNNING':self.device.result(c,'CANCELLED','VOICE_INTERRUPTED')
   self.device.expression='idle';raise
  except Exception as e:
   self.device.result(c,'REJECTED',type(e).__name__);self.device.expression='error'
 def playback(self,p,message):
  if set(message)!={'type','command_id','ended','position_ms'} or not isinstance(message['command_id'],str) or type(message['ended']) is not bool or type(message['position_ms']) is not int or not 0<=message['position_ms']<=60000:return
  ident=message['command_id'];m=self.voice_metrics.get(ident)
  if not m or ident not in self.device.results:return
  result=self.device.results[ident]
  # Playback observations refer to a command owned by this websocket; never accept audio as a motion tool.
  if result.get('client_id')!=p['client_id'] or result.get('status')!='RUNNING':return
  if message['position_ms']<m['position_ms']:return
  m['position_ms']=message['position_ms']
  if message.get('ended'):
   if m['playback_start_received_ms'] is None:return
   m['playback_end_received_ms']=self.clock();self.device.result({'command_id':ident,'type':'VOICE_SESSION','client_id':p['client_id']},'COMPLETED','HOST_PLAYBACK_REPORTED');self.device.expression='idle'
  else:
   if m['playback_start_received_ms'] is None:m['playback_start_received_ms']=self.clock()
   self.device.expression='speaking'
  return {'type':'voice_metrics','command_id':ident,'data':m}
 def interrupt_ack(self,p,message):
  if set(message)!={'type','command_id'} or not isinstance(message['command_id'],str):return
  ident=message['command_id'];m=self.voice_metrics.get(ident);result=self.device.results.get(ident,{})
  if not m or m['interrupt_requested_ms'] is None or result.get('client_id')!=p['client_id'] or result.get('status') not in ('CANCELLED','EXPIRED'):return
  if m['interrupt_complete_ms'] is None:m['interrupt_complete_ms']=self.clock()
  return {'type':'voice_metrics','command_id':ident,'data':m}
 def close(self):self.memory.close();self.auth.db.close();self.budget.close()

def create_app(directory=None,clock=None):
 g=Gateway(directory or os.environ.get('MORI_DATA_DIR','.state'),clock)
 @asynccontextmanager
 async def lifespan(app):
  async def loop():
   while True:await g.tick();await asyncio.sleep(.01)
  task=asyncio.create_task(loop())
  yield
  task.cancel()
  with contextlib.suppress(asyncio.CancelledError):await task
  for t in g.voice_tasks.values():t.cancel()
  if g.voice_tasks:await asyncio.gather(*g.voice_tasks.values(),return_exceptions=True)
  g.close()
 app=FastAPI(title='MORI V1.2 gateway',version=PROFILE['software_version'],lifespan=lifespan);app.state.gateway=g
 origins=os.environ.get('MORI_ALLOWED_ORIGINS','http://127.0.0.1:5173,http://localhost:5173,http://localhost,capacitor://localhost').split(',')
 app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'])
 async def bounded_body(request,maximum):
  data=bytearray()
  async for chunk in request.stream():
   data.extend(chunk)
   if len(data)>maximum:raise HTTPException(413,'LENGTH')
  return bytes(data)
 def identity(request):
  try:return g.auth.verify(request.headers.get('authorization','').removeprefix('Bearer '))
  except ValueError:raise HTTPException(401,'UNAUTHORIZED')
 @app.get('/health')
 def health():return {'status':'PASS','protocol':'MORI/2','source':'SIMULATED','version':PROFILE['software_version']}
 @app.post('/api/pair')
 async def pair(request:Request):
  try:
   raw=await bounded_body(request,128)
   obj=object_json(raw,128)
   if set(obj)!={'code'}:raise ValueError('FIELDS')
   return g.auth.pair(obj['code'],request.client.host if request.client else 'unknown')
  except (ValueError,KeyError,TypeError):raise HTTPException(403,'PAIRING_REJECTED')
 @app.get('/api/status')
 def status(request:Request):identity(request);return g.device.snapshot()
 @app.post('/api/command')
 async def command(request:Request):
  p=identity(request)
  try:c=parse((await bounded_body(request,4096)).decode())
  except (ValueError,UnicodeError):raise HTTPException(422,'PROTOCOL')
  return await g.dispatch(c,p)
 @app.post('/api/voice/asr')
 async def asr(request:Request):
  p=identity(request)
  if 'interaction' not in p['permissions']:raise HTTPException(403,'VOICE_PERMISSION')
  try:
   obj=object_json(await bounded_body(request,860000),860000)
   if set(obj)!={'audio_base64'}:raise ValueError()
   data=base64.b64decode(obj['audio_base64'],validate=True)
   with wave.open(io.BytesIO(data),'rb') as f:
    if f.getnchannels()!=1 or f.getsampwidth()!=2 or f.getframerate()!=16000 or f.getnframes()>320000:raise ValueError()
  except (ValueError,TypeError,wave.Error,EOFError):raise HTTPException(422,'WAV_16K_MONO_20S_REQUIRED')
  try:text=await g.services.asr(data)
  except ValueError as error:
   if str(error)=='API_BUDGET_NOT_AUTHORIZED':raise HTTPException(403,'API_BUDGET_NOT_AUTHORIZED')
   raise HTTPException(502,'ASR_PROVIDER_FAILED') from error
  except Exception as error:raise HTTPException(502,'ASR_PROVIDER_FAILED') from error
  return {'text':text,'source':g.services.source,'retained':False}
 @app.get('/api/camera/frame')
 def frame(request:Request):
  p=identity(request)
  if 'camera' not in p['permissions']:raise HTTPException(403,'CAMERA_PERMISSION')
  if g.device.camera=='OFF':raise HTTPException(409,'CAMERA_OFF')
  if g.device.camera=='SNAPSHOT':
   fid=g.device.capture();image=fixture(fid,g.scenario);g.frame_jpeg=cv2.imencode('.jpg',image)[1].tobytes()
  if not g.frame_jpeg:return Response(status_code=204,headers={'Cache-Control':'no-store','X-Mori-State':'WAITING_FOR_FRAME'})
  return Response(g.frame_jpeg,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Mori-Source':'SIMULATED','X-Capture-Frame':str(g.device.camera_frame)})
 @app.post('/api/camera/describe')
 async def describe(request:Request):
  p=identity(request)
  if 'camera' not in p['permissions'] or g.device.camera!='SNAPSHOT' or not g.device.upload_allowed:raise HTTPException(403,'SNAPSHOT_UPLOAD_CONSENT_REQUIRED')
  if not g.frame_jpeg:raise HTTPException(409,'CAPTURE_FIRST')
  return await g.services.vlm(g.frame_jpeg)
 @app.post('/api/simulation/scenario')
 async def scenario(request:Request):
  p=identity(request)
  try:
   data=object_json(await bounded_body(request,128),128)
   if set(data)!={'scenario'}:raise ValueError('FIELDS')
  except (ValueError,TypeError):raise HTTPException(400,'SCENARIO')
  if 'control' not in p['permissions'] or data.get('scenario') not in ['single','multiple','lost','dark']:raise HTTPException(400,'SCENARIO')
  g.scenario=data['scenario'];return {'source':'SIMULATED','scenario':g.scenario}
 @app.post('/api/credentials/revoke')
 def revoke(request:Request):
  p=identity(request);g.auth.revoke(p['client_id']);g.device.disconnect(p['client_id']);return {'status':'COMPLETED'}
 @app.get('/api/budget')
 def budget(request:Request):identity(request);return {'provider':g.services.source,'call_limit':g.budget.limit,'calls':g.budget.calls,'costs':g.budget.costs,'auto_recharge':False}
 @app.websocket('/ws')
 async def websocket(ws:WebSocket):
  origin=ws.headers.get('origin')
  if origin and origin not in origins:await ws.close(code=1008);return
  await ws.accept();p=None;sender=None
  async def verify_token(token):
   try:return g.auth.verify(token)
   except ValueError:
    with contextlib.suppress(RuntimeError):await ws.close(code=1008,reason='UNAUTHORIZED')
    raise
  try:
   login=await asyncio.wait_for(ws.receive_text(),5)
   login=object_json(login,256)
   if set(login)!={'token'}:raise ValueError('FIELDS')
   token=login['token'];p=await verify_token(token)
   previous=g.sockets.get(p['client_id'])
   if previous:await previous.close(code=4001,reason='CLIENT_CONNECTION_REPLACED')
   g.sockets[p['client_id']]=ws
   async def telemetry():
    transport_seq=0
    while True:
     transport_seq+=1
     try:await verify_token(token)
     except ValueError:return
     data=g.device.snapshot();data['client_sequence']=g.device.last_sequence.get(p['client_id'],0)
     await ws.send_json({'type':'telemetry','transport_seq':transport_seq,'data':data});await asyncio.sleep(.1)
   sender=asyncio.create_task(telemetry())
   while True:
    raw=await ws.receive_text();await verify_token(token)
    if len(raw)>4096:await ws.send_json({'type':'result','data':{'status':'REJECTED','reason':'LENGTH'}});continue
    try:envelope=object_json(raw)
    except (ValueError,RecursionError):envelope=None
    if isinstance(envelope,dict) and envelope.get('type') in ('playback','interrupt_ack'):
     observation=g.playback(p,envelope) if envelope['type']=='playback' else g.interrupt_ack(p,envelope)
     if observation:await ws.send_json(observation)
     continue
    try:c=parse(raw);res=await g.dispatch(c,p)
    except (ProtocolError,ValueError):res={'status':'REJECTED','reason':'PROTOCOL'}
    await ws.send_json({'type':'result','data':res})
  except (WebSocketDisconnect,ValueError,KeyError,asyncio.TimeoutError):pass
  finally:
   if sender:
    sender.cancel()
    with contextlib.suppress(asyncio.CancelledError,WebSocketDisconnect,RuntimeError):await sender
   if p:
    if g.sockets.get(p['client_id'])==ws:
     g.device.disconnect(p['client_id']);g.sockets.pop(p['client_id'],None)
   with contextlib.suppress(Exception):await ws.close()
 from .xiaozhi import install
 install(app,g,origins)
 return app
