import sys,json,math
import pcbnew as k
from layout_P3 import paths,xy,F,B
from route_local_P3 import connect
from close_routes_P2 import merge_lines,snap_via_ends
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));drc=json.loads((r/'drc.json').read_text());items={}
for f in b.GetFootprints():
 for z in f.Pads():items[z.m_Uuid.AsString()]=z
for z in b.GetTracks():items[z.m_Uuid.AsString()]=z

def coords(z):
 if isinstance(z,k.PCB_TRACK) and not isinstance(z,k.PCB_VIA):return [xy(z.GetStart()),xy(z.GetEnd())]
 return [xy(z.GetPosition())]
def layers(z):return [l for l in [F,B] if z.IsOnLayer(l)]
log=[]
for i,v in enumerate(drc['unconnected_items']):
 a,z=[items.get(vv['uuid']) for vv in v['items']]
 if a is None or z is None:log.append(dict(index=i,status='SKIPPED_ZONE'));continue
 choices=sorted([(math.dist(ap,zp),ap,zp) for ap in coords(a) for zp in coords(z)])
 for _,ap,zp in choices:
  try:
   net=str(a.GetNetname());w=.381 if 'KELVIN' in net else .2
   result=connect(b,net,ap,zp,layers(a),layers(z),{'imu':(20,16),'motion':(70,35),'power':(80,55)}[kind],step=.05,width=w)
   result.update(index=i,status='ROUTED');log.append(result);k.SaveBoard(str(p),b);break
  except RuntimeError as exc:reason=str(exc)
 else:log.append(dict(index=i,status='BLOCKED',reason=reason));print('BLOCKED',i,reason,flush=True)
 (r/'close_remaining.json').write_text(json.dumps(log,indent=2)+'\n')
(r/'close_remaining.json').write_text(json.dumps(log,indent=2)+'\n')
merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
