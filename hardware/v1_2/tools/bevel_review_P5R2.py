"""Replace undersized free corner bevels with the user's 0.499999mm setback.
Every retained/rejected candidate remains in the log; no DRC exemptions.
"""
import sys,math,collections,pcbnew as k
from review_edit_P5R2 import Edit,xy,F,B
from geometry_guard_P5 import Guard
from layout_P5 import pt,mm
e=Edit(sys.argv[1]);tried=set()
def key(p):return tuple(round(q,4)for q in p)
while True:
 ts=[t for t in e.b.GetTracks()if not isinstance(t,k.PCB_VIA)];nodes=collections.defaultdict(list)
 for t in ts:
  for q in[xy(t.GetStart()),xy(t.GetEnd())]:nodes[t.GetNetname(),t.GetLayer(),key(q)].append(t)
 candidates=[]
 for t in ts:
  uid=t.m_Uuid.AsString();a,z=xy(t.GetStart()),xy(t.GetEnd());dx,dy=z[0]-a[0],z[1]-a[1]
  if uid in tried or not(.01<abs(dx)<.4999 and abs(abs(dx)-abs(dy))<.0001):continue
  net,l=t.GetNetname(),t.GetLayer();groups=[nodes[net,l,key(v)]for v in[a,z]]
  if any(len(g)!=2 for g in groups):continue
  nbs=[next(u for u in g if u!=t)for g in groups]
  if any(u.GetWidth()!=t.GetWidth()for u in nbs):continue
  ends=[xy(u.GetEnd())if key(xy(u.GetStart()))==key(v)else xy(u.GetStart())for u,v in zip(nbs,[a,z])]
  vectors=[(v[0]-end[0],v[1]-end[1])for end,v in zip(ends,[a,z])]
  typ=[]
  for vx,vy in vectors:typ.append('h'if abs(vy)<.0001 and abs(vx)>.5 else'v'if abs(vx)<.0001 and abs(vy)>.5 else'bad')
  if sorted(typ)!=['h','v']:continue
  corner=(z[0],a[1])if typ[0]=='h'else(a[0],z[1]);dists=[math.dist(v,corner)for v in ends]
  if min(dists)<.5001:continue
  # Real pad/via junctions are not free corners, and must remain intact.
  if any(q.IsOnLayer(l)and q.GetNetname()==net and any(q.GetEffectiveShape(l).Collide(pt(*v),mm(.01))for v in[a,z])for f in e.b.GetFootprints()for q in f.Pads()):continue
  if any(isinstance(v,k.PCB_VIA)and v.GetNetname()==net and min(math.dist(xy(v.GetPosition()),q)for q in[a,z])<.45 for v in e.b.GetTracks()):continue
  p1=tuple(corner[i]+(ends[0][i]-corner[i])*.499999/dists[0]for i in range(2));p2=tuple(corner[i]+(ends[1][i]-corner[i])*.499999/dists[1]for i in range(2));path=[ends[0],p1,p2,ends[1]]
  g=Guard(e.b,net);w=k.ToMM(t.GetWidth())
  if not all(g.line_clear(u,v,l,w)for u,v in zip(path,path[1:])):
   tried.add(uid);continue
  candidates.append((uid,nbs,path,net,l,w))
 if not candidates:break
 uid,nbs,path,net,l,w=candidates[0];tried.add(uid);e.remove([uid]+[t.m_Uuid.AsString()for t in nbs]);e.add(net,l,path,w);e.commit('R14 short bevel expanded to exact 0.499999 mm setback on '+net)
