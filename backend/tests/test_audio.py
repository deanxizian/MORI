import asyncio,io,wave,pytest
from backend.mori.audio_codec import encode_tts,OpusCapture
from backend.mori.providers import MockServices,Budget
from backend.mori.app import create_app
from fastapi.testclient import TestClient
from simulation.harness import Clock,Rig

def test_codec_real_opus_roundtrip():
 wav=asyncio.run(MockServices().tts('测试'));packets=encode_tts(wav);assert packets
 c=OpusCapture()
 for p in packets:assert 0<len(p)<=1275;c.feed(p)
 with wave.open(io.BytesIO(c.wav())) as f:assert f.getframerate()==16000 and f.getnframes()>=3200
 with pytest.raises(ValueError):c.feed(b'x'*1276)

def test_budget_survives_restart(tmp_path):
 p=tmp_path/'budget.sqlite';b=Budget(1,p);b.charge('ASR');b.close();b=Budget(1,p)
 with pytest.raises(ValueError):b.charge('LLM')
 assert b.calls==1;b.close()

def test_xiaozhi_hello_voice_abort_no_tools(tmp_path):
 app=create_app(tmp_path);g=app.state.gateway
 with TestClient(app) as client:
  p=g.auth.create('owner',['interaction']);packets=encode_tts(asyncio.run(MockServices().tts('test')))
  with client.websocket_connect('/xiaozhi/v1',headers={'Authorization':'Bearer '+p['token']}) as ws:
   ws.send_json({'type':'hello','version':1,'audio_params':{'format':'opus','sample_rate':16000,'channels':1,'frame_duration':60}});assert ws.receive_json()['features']['mcp'] is False
   ws.send_json({'type':'listen','state':'start'})
   for packet in packets:ws.send_bytes(packet)
   ws.send_json({'type':'listen','state':'stop'});assert ws.receive_json()['type']=='stt';assert ws.receive_json()['state']=='start';assert ws.receive_json()['state']=='sentence_start'
   packet=ws.receive_bytes();assert packet
   ws.send_json({'type':'abort'})
   while True:
    r=ws.receive()
    if r.get('text'):
     import json
     if json.loads(r['text']).get('reason')=='aborted':break
   ws.send_json({'type':'mcp','payload':{'command':'raw_pwm'}});assert 'UNAUTHORIZED' in ws.receive_json()['message']

def test_interrupt_is_complete_only_after_owned_playback_ack(tmp_path):
 from backend.mori.app import Gateway
 async def exercise():
  clock=Clock();g=Gateway(tmp_path,clock);r=Rig();r.d=g.device
  p=g.auth.create('owner',['interaction']);cid=p['client_id']
  c=r.cmd('VOICE_SESSION',{'action':'text','text':'你好'},client=cid)
  assert (await g.dispatch(c,p))['status']=='RUNNING'
  await g.voice_tasks[cid]
  ident=c['command_id'];m=g.voice_metrics[ident]
  # Generated audio is not playback. A request to cancel is not an acoustic completion.
  assert m['playback_start_received_ms'] is None
  clock.step(10)
  g.playback(p,{'type':'playback','command_id':ident,'ended':False,'position_ms':0})
  await g.dispatch(r.cmd('VOICE_SESSION',{'action':'interrupt','text':''},client=cid),p)
  assert g.device.results[ident]['status']=='CANCELLED'
  assert m['interrupt_complete_ms'] is None
  assert m['interrupt_requested_ms']==clock()
  ack={'type':'interrupt_ack','command_id':ident}
  g.interrupt_ack({'client_id':'other'},ack)
  assert m['interrupt_complete_ms'] is None
  clock.step(12);g.interrupt_ack(p,ack)
  assert m['interrupt_complete_ms']==clock()
  g.playback(p,{'type':'playback','command_id':[], 'ended':False,'position_ms':0})
  c=r.cmd('VOICE_SESSION',{'action':'text','text':'等待播放超时'},client=cid)
  await g.dispatch(c,p);await g.voice_tasks[cid]
  clock.step(90001);await g.tick()
  assert g.device.results[c['command_id']]['status']=='EXPIRED'
  g.close()
 asyncio.run(exercise())

def test_valid_wav_provider_error_is_not_reported_as_bad_audio(tmp_path):
 import base64
 app=create_app(tmp_path);g=app.state.gateway
 class Denied:
  source='TEST'
  async def asr(self,data):raise ValueError('API_BUDGET_NOT_AUTHORIZED')
 g.services=Denied()
 with TestClient(app) as client:
  p=g.auth.create('owner',['interaction']);headers={'Authorization':'Bearer '+p['token']}
  data=asyncio.run(MockServices().tts('test'))
  response=client.post('/api/voice/asr',headers=headers,json={'audio_base64':base64.b64encode(data).decode()})
  assert response.status_code==403 and response.json()['detail']=='API_BUDGET_NOT_AUTHORIZED'
  response=client.post('/api/voice/asr',headers=headers,json={'audio_base64':'bad'})
  assert response.status_code==422
