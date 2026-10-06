"""Conservative native-shape-checked removal of acute T branches.

Projects retain their original 60 degree rule. No DRC exemption is created.
"""
import math,json,sys
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm
from close_routes_P2 import merge_lines,snap_via_ends
from geometry_guard_P3R1 import Guard
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));report=json.loads((r/'drc.json').read_text());tracks={t.m_Uuid.AsString():t for t in b.GetTracks()};log=[]
def point_segment(p,a,z):
 vx,vy=z[0]-a[0],z[1]-a[1];t=((p[0]-a[0])*vx+(p[1]-a[1])*vy)/(vx*vx+vy*vy);q=(a[0]+t*vx,a[1]+t*vy);return math.dist(p,q),t,q
def clear(t,a,z):
 return Guard(b,t.GetNetname()).line_clear(a,z,t.GetLayer(),k.ToMM(t.GetWidth()))
 # Retained historical implementation below is unreachable; native-shaped
 # Guard now also respects the net-selective package escape areas.
 radius=k.ToMM(t.GetWidth())/2;layer=t.GetLayer();items=[]
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.IsOnLayer(layer) and q.GetNetCode()!=t.GetNetCode():items.append((q.GetEffectiveShape(layer),radius+.202))
 for q in b.GetTracks():
  if q.IsOnLayer(layer) and q.GetNetCode()!=t.GetNetCode():items.append((q.GetEffectiveShape(layer),radius+.202))
 for q in b.Zones():
  if q.GetIsRuleArea() and q.IsOnLayer(layer) and q.GetDoNotAllowTracks():items.append((q.Outline(),radius+.002))
 n=max(1,math.ceil(math.dist(a,z)/.04))
 for i in range(n+1):
  v=pt(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n)
  if any(sh.Collide(v,mm(cl)) for sh,cl in items):return False
 return True
seen=set()
for v in report['violations']:
 if v['type']!='track_angle':continue
 ids=tuple(sorted(it['uuid'] for it in v['items']))
 if ids in seen:continue
 seen.add(ids);ts=[tracks.get(i) for i in ids]
 if any(t is None or isinstance(t,k.PCB_VIA) for t in ts):continue
 choices=[]
 for moving,stem in [ts,list(reversed(ts))]:
  a,z=xy(stem.GetStart()),xy(stem.GetEnd())
  for which,near,far in [(0,xy(moving.GetStart()),xy(moving.GetEnd())),(1,xy(moving.GetEnd()),xy(moving.GetStart()))]:
   dist,t,_=point_segment(near,a,z)
   if dist>k.ToMM(moving.GetWidth()+stem.GetWidth())/2+.01 or not -.03<t<1.03:continue
   # Do not detach another branch, terminal or via at the old junction.
   if any(q.GetNetCode()==moving.GetNetCode() and q.IsOnLayer(moving.GetLayer()) and q.GetEffectiveShape(moving.GetLayer()).Collide(pt(*near),moving.GetWidth()//2+mm(.01)) for f in b.GetFootprints() for q in f.Pads()):continue
   if any(q.m_Uuid.AsString() not in [moving.m_Uuid.AsString(),stem.m_Uuid.AsString()] and q.GetNetCode()==moving.GetNetCode() and q.IsOnLayer(moving.GetLayer()) and q.GetEffectiveShape(moving.GetLayer()).Collide(pt(*near),moving.GetWidth()//2+mm(.01)) for q in b.GetTracks()):continue
   _,t,proj=point_segment(far,a,z)
   if not 0<=t<=1 or math.dist(near,proj)>4 or math.dist(far,proj)<.02:continue
   if math.dist(far,proj)>math.dist(far,near)+.02:continue
   if clear(moving,far,proj):choices.append((math.dist(far,proj),moving,which,near,proj,far))
 if not choices:continue
 _,t,which,old,new,far=min(choices,key=lambda x:x[0]);(t.SetStart if which==0 else t.SetEnd)(pt(*new));log.append(dict(uuid=t.m_Uuid.AsString(),net=str(t.GetNetname()),old=old,new=new,other=far))
# R39 source demands the actual 0.381 mm Kelvin width, including fanout.
if kind=='power':
 for t in b.GetTracks():
  if not isinstance(t,k.PCB_VIA) and str(t.GetNetname()) in ['/KELVIN_P','/KELVIN_N']:t.SetWidth(mm(.381))
merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
old=json.loads((r/'tidy_changes.json').read_text()) if (r/'tidy_changes.json').exists() else []
(r/'tidy_changes.json').write_text(json.dumps(old+log,indent=2)+'\n');print(name,'simplified',len(log),'acute branches',flush=True)
