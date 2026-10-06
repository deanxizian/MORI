"""Join separate ground regions using real filled-zone geometry.

Endpoints are on copper, not merely the centres of pads surrounded by signals.
Keepouts and native clearances are respected; native DRC is still required.
"""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,F,B
from geometry_guard_P3R1 import Guard
from route_local_P3R1 import connect

kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p))
size={'power':(80,55),'motion':(70,35),'imu':(20,16)}[kind]

def regions():
 items=[];parent=[];ids={}
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 def add(label,shape,layer,uid):
  i=len(items);items.append((label,shape,layer));parent.append(i)
  if uid in ids:parent[root(i)]=root(ids[uid])
  else:ids[uid]=i
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.GetNetname()=='/GND':
    for l in [F,B]:
     if q.IsOnLayer(l):add(f.GetReference()+'.'+q.GetNumber(),q.GetEffectiveShape(l),l,q.m_Uuid.AsString())
 for q in b.GetTracks():
  if q.GetNetname()=='/GND':
   for l in [F,B]:
    if q.IsOnLayer(l):add('track',q.GetEffectiveShape(l),l,q.m_Uuid.AsString())
 for z in b.Zones():
  if not z.GetIsRuleArea() and z.GetNetname()=='/GND':
   shape=z.GetFilledPolysList(z.GetLayer())
   for i in range(shape.OutlineCount()):add('zone',shape.Subset(i,i+1),z.GetLayer(),z.m_Uuid.AsString()+str(i))
 for i,a in enumerate(items):
  for j in range(i):
   z=items[j]
   if a[2]==z[2] and root(i)!=root(j) and a[1].BBox().Intersects(z[1].BBox()) and a[1].Collide(z[1],0):parent[root(i)]=root(j)
 groups={}
 for i,item in enumerate(items):groups.setdefault(root(i),[]).append(item)
 return sorted(groups.values(),key=len,reverse=True)

def samples(group,g,step):
 out=set()
 for label,sh,l in group:
  if label!='zone':continue
  bb=sh.BBox();x1,y1,x2,y2=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
  for ix in range(math.ceil(x1/step),math.floor(x2/step)+1):
   for iy in range(math.ceil(y1/step),math.floor(y2/step)+1):
    q=(ix*step,iy*step)
    if (q[0],q[1],l) not in out and sh.Collide(pt(*q),0) and g.clear(q,l,.25):out.add((q[0],q[1],l))
 return out

log=[]
for iteration in range(6):
 groups=regions();print(kind,'ground regions',len(groups),[len(q) for q in groups],flush=True)
 if len(groups)==1:break
 g=Guard(b,'/GND');main=samples(groups[0],g,.5);success=False
 for group in groups[1:]:
  pts=samples(group,g,.25);pairs=[]
  # Keep several spatially distinct nearest candidates.
  for a in pts:
   nearest=sorted(main,key=lambda z:math.dist(a[:2],z[:2])+(0 if a[2]==z[2] else 1.5))[:3]
   for z in nearest:pairs.append((math.dist(a[:2],z[:2])+(0 if a[2]==z[2] else 1.5),a,z))
  chosen=[]
  for dist,a,z in sorted(pairs):
   if any(math.dist(a[:2],aa[:2])<.75 and a[2]==aa[2] for aa in chosen):continue
   chosen.append(a)
   try:
    res=connect(b,'/GND',a[:2],z[:2],[a[2]],[z[2]],size,step=.05,width=.25,vd=.8,dr=.3,max_nodes=220000,time_limit=18)
    log.append(res);success=True;break
   except RuntimeError as e:print('ground bridge candidate',a,z,str(e),flush=True)
   if len(chosen)>=6:break
  if success:break
 if not success:print('Remaining regions need placement or signal-corridor change',flush=True);break
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'ground_region_bridges.json').write_text(json.dumps(log,indent=2)+'\n')
