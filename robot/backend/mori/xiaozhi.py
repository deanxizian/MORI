"""Small protocol adapter derived from the pinned Xiaozhi WebSocket v1 spec.
Not a fork of Xiaozhi application loops. No MCP/shell/raw motor tools accepted.
"""
import asyncio,contextlib,json,uuid,time
from fastapi import WebSocket,WebSocketDisconnect
from .audio_codec import OpusCapture,encode_tts
from .inputs import object_json

def install(app,g,origins):
 @app.websocket('/xiaozhi/v1')
 async def websocket(ws:WebSocket):
  try:
   p=g.auth.verify(ws.headers.get('authorization','').removeprefix('Bearer '))
   if 'interaction' not in p['permissions'] or (ws.headers.get('origin') and ws.headers['origin'] not in origins):raise ValueError('AUTHORIZATION')
  except ValueError:await ws.close(code=1008);return
  await ws.accept();session=uuid.uuid4().hex;capture=None;task=None;hello=False
  async def conversation(wav):
   start=g.clock();text=await g.services.asr(wav);await ws.send_json({'type':'stt','text':text,'session_id':session,'source':g.services.source})
   # Exact spoken stop is a high-level stop. No model output is executed as a command.
   if text.strip() in ('停下','停止移动'):g.device.cancel('VOICE_STOP_MOTION')
   reply=await g.services.llm(text,g.memory.query(p['user_id'],g.device.device_id,text[:64]));audio=await g.services.tts(reply)
   packets=await asyncio.to_thread(encode_tts,audio)
   await ws.send_json({'type':'tts','state':'start','session_id':session,'source':g.services.source})
   await ws.send_json({'type':'tts','state':'sentence_start','text':reply,'session_id':session})
   for packet in packets:await ws.send_bytes(packet);await asyncio.sleep(.06)
   await ws.send_json({'type':'tts','state':'stop','session_id':session,'metrics':{'requested_ms':start,'audio_transport_done_ms':g.clock(),'actual_device_playback_ms':None,'actual_device_playback_status':'NOT_TESTED'}})
  try:
   while True:
    g.auth.verify(ws.headers.get('authorization','').removeprefix('Bearer '))
    item=await asyncio.wait_for(ws.receive(),30)
    if item['type']=='websocket.disconnect':break
    if item.get('bytes') is not None:
     if capture is None:raise ValueError('LISTEN_START_REQUIRED')
     capture.feed(item['bytes']);continue
    raw=item.get('text','')
    if len(raw.encode())>4096:raise ValueError('LENGTH')
    data=object_json(raw);kind=data.get('type')
    if kind=='hello':
     a=data.get('audio_params',{})
     if data.get('version')!=1 or a.get('format')!='opus' or a.get('sample_rate')!=16000 or a.get('channels')!=1 or a.get('frame_duration')!=60:raise ValueError('AUDIO_CONTRACT')
     hello=True;await ws.send_json({'type':'hello','transport':'websocket','session_id':session,'version':1,'features':{'mcp':False,'aec':False,'half_duplex':True},'audio_params':{'format':'opus','sample_rate':24000,'channels':1,'frame_duration':60}})
    elif not hello:raise ValueError('HELLO_REQUIRED')
    elif kind=='abort':
     if task:task.cancel();await asyncio.gather(task,return_exceptions=True)
     capture=None;await ws.send_json({'type':'tts','state':'stop','session_id':session,'reason':'aborted'})
    elif kind=='listen' and data.get('state')=='start':
     if task:task.cancel();await asyncio.gather(task,return_exceptions=True)
     capture=OpusCapture()
    elif kind=='listen' and data.get('state')=='stop' and capture:
     task=asyncio.create_task(conversation(capture.wav()));capture=None
    else:await ws.send_json({'type':'error','message':'UNSUPPORTED_OR_UNAUTHORIZED_TOOL'})
  except (WebSocketDisconnect,ValueError,KeyError,asyncio.TimeoutError):pass
  finally:
   if task:task.cancel();await asyncio.gather(task,return_exceptions=True)
   with contextlib.suppress(Exception):await ws.close()
