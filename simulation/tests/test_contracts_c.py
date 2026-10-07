import ctypes as c,json,pathlib,subprocess,time,statistics,zlib,struct,pytest,math
from contracts.protocol import parse,validate,ProtocolError
from contracts.wire import encode,Decoder
ROOT=pathlib.Path(__file__).resolve().parents[2]
class Eye(c.Structure):_fields_=[(k,c.c_float) for k in ['x','y','a','b','c','d','w','h']]
class Eyes(c.Structure):_fields_=[('state',c.c_int),('start',c.c_float),('transition',c.c_bool),('from_',Eye*2)]
class Wire(c.Structure):_fields_=[('bytes',c.c_uint8*158),('used',c.c_size_t),('started_ms',c.c_uint64),('dropped',c.c_uint32)]
@pytest.fixture(scope='module')
def lib(tmp_path_factory):
 path=tmp_path_factory.mktemp('c')/'libmori.so'
 subprocess.run(['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','-fPIC','contracts/wire.c','firmware/interaction/core/eyes.c','-lm','-o',str(path)],cwd=ROOT,check=True)
 l=c.CDLL(str(path));l.mori_wire_feed.argtypes=[c.POINTER(Wire),c.c_uint8,c.c_uint64];l.mori_wire_feed.restype=c.c_bool
 l.mori_eyes_sample.argtypes=[c.POINTER(Eyes),c.c_float,c.c_float,c.POINTER(Eye)];l.mori_eyes_sample.restype=c.c_bool
 l.mori_eyes_state.argtypes=[c.POINTER(Eyes),c.c_int,c.c_float,c.c_float];l.mori_eyes_state.restype=c.c_bool
 l.mori_eyes_render.argtypes=[c.POINTER(Eye),c.POINTER(c.c_uint16),c.c_int,c.c_int];return l

def test_json_corpus_and_nonfinite():
 for v in json.loads((ROOT/'contracts/test_vectors.json').read_text()):
  if v['valid']:assert validate(v['command'])
  else:
   with pytest.raises(ProtocolError):validate(v['command'])
 base=json.loads((ROOT/'contracts/test_vectors.json').read_text())[0]['command']
 for x in [float('nan'),float('inf'),-float('inf')]:
  base['params']['v_m_s']=x
  with pytest.raises(ProtocolError):parse(json.dumps(base))
 with pytest.raises(ProtocolError):parse('{"x":1,"x":2}')
 with pytest.raises(ProtocolError):parse(' '*4097)
 with pytest.raises(ProtocolError):parse('{')

def test_crc_fragmentation_timeout_resync_and_overflow(lib):
 valid=encode(3,5,99,44,b'payload');bad=bytearray(valid);bad[-1]^=1
 for packet,accepted in [(valid,1),(bad,0),(b'garbage'+valid,1),(valid[:-1],0), (b'\xa5\x5a\x02\x03\xff\xff'+bytes(20)+valid,1)]:
  w=Wire();d=Decoder();n=0;py=[]
  for b in packet:n+=int(lib.mori_wire_feed(c.byref(w),b,100));py+=d.feed(bytes([b]),100)
  assert n==len(py)==accepted;assert w.used<=158
 w=Wire();d=Decoder()
 for b in valid[:10]:lib.mori_wire_feed(c.byref(w),b,100)
 d.feed(valid[:10],100);assert not d.feed(valid[10:],151)
 assert sum(lib.mori_wire_feed(c.byref(w),b,151) for b in valid[10:])==0
 assert sum(lib.mori_wire_feed(c.byref(w),b,152) for b in valid)==1
 for k in range(256):
  packet=bytes([k])*200+valid;w=Wire();n=sum(lib.mori_wire_feed(c.byref(w),b,200) for b in packet);assert n>=1

def test_eyes_c_ts_and_round_crop_benchmark(lib):
 frames=json.loads((ROOT/'reports/v1/tests/eyes_ts_frames.json').read_text());states=['idle','listening','thinking','speaking','happy','confused','sleep_visual','error'];engine=Eyes();out=(Eye*2)();worst=0
 for record in frames:
  if record['change']:assert lib.mori_eyes_state(c.byref(engine),states.index(record['state']),record['t'],record['rms'])
  assert lib.mori_eyes_sample(c.byref(engine),record['t'],record['rms'],out)
  for i,e in enumerate(record['frame']):
   for k,value in e.items():worst=max(worst,abs(getattr(out[i],k)-value))
 assert worst<.0002
 assert not lib.mori_eyes_sample(c.byref(engine),float('nan'),0,out)
 timings={}
 for width in (240,360):
  pixels=(c.c_uint16*(width*width))();us=[]
  for _ in range(30):
   start=time.perf_counter_ns();lib.mori_eyes_render(out,pixels,width,width);us.append((time.perf_counter_ns()-start)/1000)
  for y in range(width):
   for x in range(width):
    if math.hypot(x+.5-width/2,y+.5-width/2)>=width*.46:assert pixels[y*width+x]==0
  assert set(pixels)<={0,0xf7be};assert 0xf7be in pixels
  timings[str(width)]={'source':'HOST','status':'PASS','samples':len(us),'memory_bytes':width*width*2,'p50_us':statistics.median(us),'p95_us':sorted(us)[28],'max_us':max(us),'hardware_max_us':None,'hardware_status':'NOT_TESTED'}
 (ROOT/'reports/v1/eyes_render_host.json').write_text(json.dumps({'max_geometry_difference':worst,'resolutions':timings},indent=2))

def test_extreme_json_integer_is_rejected_without_server_exception():
 base=json.loads((ROOT/'contracts/test_vectors.json').read_text())[0]['command'];base['params']['v_m_s']=10**1000
 with pytest.raises(ProtocolError):parse(json.dumps(base))
