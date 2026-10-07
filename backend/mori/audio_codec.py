"""Opus frames used by Xiaozhi v1, bounded 16 kHz mono input / 24 kHz output.
PyAV and FFmpeg codec versions are recorded in the environment report.
"""
import av,io,wave,numpy as np
class OpusCapture:
 def __init__(self):
  self.decoder=av.CodecContext.create('opus','r');self.decoder.extradata=b'OpusHead'+bytes([1,1])+b'\x00\x00'+(16000).to_bytes(4,'little')+b'\x00\x00\x00'
  self.resampler=av.AudioResampler(format='s16',layout='mono',rate=16000);self.pcm=bytearray();self.packets=0
 def feed(self,packet):
  if not 1<=len(packet)<=1275 or self.packets>=334:raise ValueError('OPUS_PACKET_LIMIT')
  self.packets+=1
  for frame in self.decoder.decode(av.Packet(packet)):
   for f in self.resampler.resample(frame):self.pcm.extend(f.to_ndarray().tobytes())
  if len(self.pcm)>640000:raise ValueError('AUDIO_DURATION_LIMIT')
 def wav(self):
  out=io.BytesIO()
  with wave.open(out,'wb') as f:f.setparams((1,2,16000,0,'NONE','not compressed'));f.writeframes(self.pcm)
  return out.getvalue()

def encode_tts(wav):
 resampler=av.AudioResampler(format='s16',layout='mono',rate=24000);parts=[]
 with av.open(io.BytesIO(wav)) as container:
  for frame in container.decode(audio=0):
   for f in resampler.resample(frame):parts.append(f.to_ndarray().reshape(-1))
  for f in resampler.resample(None):parts.append(f.to_ndarray().reshape(-1))
 pcm=np.concatenate(parts) if parts else np.zeros(0,np.int16)
 if len(pcm)>24000*60:raise ValueError('TTS_DURATION_LIMIT')
 codec=av.CodecContext.create('libopus','w');codec.sample_rate=24000;codec.layout='mono';codec.format='s16';codec.options={'frame_duration':'60','application':'voip'};codec.open();packets=[]
 for i in range(0,len(pcm),1440):
  data=np.zeros((1,1440),np.int16);data[0,:min(1440,len(pcm)-i)]=pcm[i:i+1440]
  f=av.AudioFrame.from_ndarray(data,format='s16',layout='mono');f.sample_rate=24000;f.pts=i
  packets.extend(bytes(p) for p in codec.encode(f))
 packets.extend(bytes(p) for p in codec.encode(None));return packets
