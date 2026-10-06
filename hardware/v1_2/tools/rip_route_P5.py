"""Route an unresolved P5 net through an explicit corridor, displacing only
interfering thin signal tracks. Fixed geometry, power conductors and body
projections stay hard constraints. Every displaced net must be reconnected.
"""
import sys,time,json,math
import pcbnew as k
from layout_P5 import *
from close_P5 import clusters,run
from route_native_P5 import connect

def rip(kind,net,width=.2):
 if not net.startswith('/'):net='/'+net
 n,d,p,r=paths(kind);b=k.LoadBoard(str(p));size=json.loads((d/'connectivity.json').read_text())['size'];cs=clusters(b,net)
 if len(cs)<=1:return []
 candidates=[]
 for t in b.GetTracks():
  if t.GetNetname() in [net,'/GND','/+3V3'] or isinstance(t,k.PCB_VIA):continue
  if k.ToMM(t.GetWidth())>.25 or k.ToMM(t.GetLength())<1.2:continue
  candidates.append(t)
 for t in candidates:b.Remove(t)
 soft=[(t.GetEffectiveShape(t.GetLayer()),t.GetLayer()) for t in candidates];oldids={t.m_Uuid.AsString() for t in b.GetTracks()};pairs=[]
 for i,x in enumerate(cs):
  for z in cs[i+1:]:
   for a,als in x.items():
    for v,vls in z.items():pairs.append((math.dist(a,v),a,v,list(als),list(vls)))
 result=None
 for dist,a,z,als,zls in sorted(pairs)[:6]:
  try:
   result=connect(b,net,a,z,als,zls,size,step=.1016,width=width,vd=1 if width>.6 else .8,dr=.45 if width>.6 else .3,time_limit=35,max_nodes=500000,heuristic_weight=3.2,soft_shapes=soft);break
  except RuntimeError as e:print('rip try',net,str(e),flush=True)
 if result is None:
  for t in candidates:b.Add(t)
  return []
 added=[t for t in b.GetTracks() if t.m_Uuid.AsString() not in oldids];hits=[]
 for t in candidates:
  l=t.GetLayer()
  if any(q.IsOnLayer(l) and q.GetEffectiveShape(l).Collide(t.GetEffectiveShape(l),mm(.205)) for q in added):
   hits.append(dict(uuid=t.m_Uuid.AsString(),net=str(t.GetNetname()),start=xy(t.GetStart()),end=xy(t.GetEnd()),width=k.ToMM(t.GetWidth())))
  else:b.Add(t)
 k.SaveBoard(str(p),b);(r/('corridor_displacement_'+str(int(time.time()))+'.json')).write_text(json.dumps(dict(net=net,result=result,displaced=hits),indent=2)+'\n')
 print('CORRIDOR',net,'displaced',len(hits),'tracks',sorted({q['net'] for q in hits}),flush=True)
 return sorted({q['net'] for q in hits})
if __name__=='__main__':
 kind=sys.argv[1];displaced=set()
 for net in sys.argv[2:]:displaced.update(rip(kind,net))
 if displaced:run(kind,sorted(displaced))
