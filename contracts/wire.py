"""Bounded local link. CRC detects damage, never authenticates a caller."""
import struct,zlib
MAGIC=b'\xA5\x5A';MAX_PAYLOAD=128;HEADER=struct.Struct('<2sBBHIQQ')
def encode(kind,sequence,session,command,payload=b''):
 if not 1<=kind<=255 or not 1<=sequence<=0x7fffffff or not 0<session<2**64 or not 0<command<2**64 or len(payload)>MAX_PAYLOAD:raise ValueError('wire range')
 h=HEADER.pack(MAGIC,2,kind,len(payload),sequence,session,command)+payload
 return h+struct.pack('<I',zlib.crc32(h))
class Decoder:
 def __init__(self):self.buffer=bytearray();self.started=0;self.dropped=0
 def feed(self,data,now_ms):
  if self.buffer and now_ms-self.started>50:self.buffer.clear();self.dropped+=1
  out=[]
  for b in data:
   if not self.buffer:self.started=now_ms
   self.buffer.append(b)
   while self.buffer and not MAGIC.startswith(self.buffer[:2]):del self.buffer[0];self.dropped+=1
   if len(self.buffer)<HEADER.size:continue
   _,v,k,n,seq,session,cmd=HEADER.unpack(self.buffer[:HEADER.size])
   if v!=2 or n>MAX_PAYLOAD or not 0<seq<=0x7fffffff or k==0 or not session or not cmd:self.buffer.clear();self.dropped+=1;continue
   total=HEADER.size+n+4
   if len(self.buffer)==total:
    frame=bytes(self.buffer);self.buffer.clear()
    if zlib.crc32(frame[:-4])!=struct.unpack('<I',frame[-4:])[0]:self.dropped+=1;continue
    out.append((k,seq,session,cmd,frame[HEADER.size:-4]))
  return out
