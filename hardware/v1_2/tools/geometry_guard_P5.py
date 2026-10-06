"""Native-shape checks for local edits. Always follow with native DRC."""
import math
import pcbnew as k
from layout_P5 import xy,pt,mm,F,B

def obstacles(b,net,point,layer,width=.2,is_via=False):
 result=[];radius=width/2;v=pt(*point)
 for f in b.GetFootprints():
  for p in f.Pads():
   if p.IsOnLayer(layer) and (is_via or p.GetNetname()!=net) and p.GetEffectiveShape(layer).Collide(v,mm(radius+.205)):
    result.append((f.GetReference()+'.'+p.GetNumber(),str(p.GetNetname())))
 for t in b.GetTracks():
  if t.GetNetname()==net:continue
  if t.IsOnLayer(layer) and t.GetEffectiveShape(layer).Collide(v,mm(radius+.205)):
   result.append((t.m_Uuid.AsString(),str(t.GetNetname())))
 for z in b.Zones():
  if not z.GetIsRuleArea() or not z.IsOnLayer(layer):continue
  forbid=z.GetDoNotAllowVias() if is_via else z.GetDoNotAllowTracks()
  if z.GetZoneName().startswith('NETBODY_'):
   f=next(f for f in b.GetFootprints() if f.GetReference()==z.GetZoneName()[8:].removesuffix('_OPPOSITE'))
   forbid=net not in {p.GetNetname() for p in f.Pads()}
  # Preserve signal-only restrictions on motion logic areas.
  if not is_via and z.GetZoneName().startswith('OUTWARD_U') and net not in ['/GND','/+3V3','/CAM_3V3']:forbid=True
  if forbid and z.Outline().Collide(v,mm(radius+.002)):result.append((z.GetZoneName(),'KEEP_OUT'))
 return result

def via_clear(b,net,p,vd=.8):return not any(obstacles(b,net,p,l,vd,True) for l in [F,B])
def line_clear(b,net,a,z,layer,width=.2):
 n=max(1,math.ceil(math.dist(a,z)/.025))
 return all(not obstacles(b,net,(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n),layer,width) for i in range(n+1))

class Guard:
 def __init__(self,b,net):
  from collections import defaultdict
  self.items=[];self.cells=defaultdict(list);self.net=net
  self.own_vias=[xy(t.GetPosition()) for t in b.GetTracks() if isinstance(t,k.PCB_VIA) and t.GetNetname()==net]
  def add(shape,layer,ownpad=False,via_only=False,clearance=.205,tracks_only=False):
   i=len(self.items);self.items.append((shape,ownpad,via_only,clearance,tracks_only));bb=shape.BBox();x1,y1,x2,y2=[k.ToMM(v) for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
   for ix in range(math.floor((x1-2)/2),math.floor((x2+2)/2)+1):
    for iy in range(math.floor((y1-2)/2),math.floor((y2+2)/2)+1):self.cells[ix,iy,layer].append(i)
  for f in b.GetFootprints():
   for p in f.Pads():
    for l in [F,B]:
     if p.IsOnLayer(l):add(p.GetEffectiveShape(l),l,p.GetNetname()==net)
  for t in b.GetTracks():
   if t.GetNetname()==net:continue
   for l in [F,B]:
    if t.IsOnLayer(l):add(t.GetEffectiveShape(l),l)
  for z in b.Zones():
   if not z.GetIsRuleArea():continue
   forbid=z.GetDoNotAllowTracks() or (z.GetZoneName().startswith('OUTWARD_U') and net not in ['/GND','/+3V3','/CAM_3V3'])
   if z.GetZoneName().startswith('NETBODY_'):
    f=next(f for f in b.GetFootprints() if f.GetReference()==z.GetZoneName()[8:].removesuffix('_OPPOSITE'))
    forbid=net not in {p.GetNetname() for p in f.Pads()}
   for l in [F,B]:
    if z.IsOnLayer(l) and (forbid or z.GetDoNotAllowVias()):add(z.Outline(),l,False,not forbid,.002,forbid and not z.GetDoNotAllowVias() and not z.GetZoneName().startswith('NETBODY_'))
 def clear(self,p,layer,width=.2,is_via=False):
  v=pt(*p)
  for i in self.cells[math.floor(p[0]/2),math.floor(p[1]/2),layer]:
   sh,own,vo,cl,to=self.items[i]
   if (own or vo) and not is_via:continue
   if to and is_via:continue
   if sh.Collide(v,mm(width/2+cl)):return False
  return True
 def via_clear(self,p,vd=.8):return not any(math.dist(p,v)<max(.82,vd) for v in self.own_vias) and all(self.clear(p,l,vd,True) for l in [F,B])
 def line_clear(self,a,z,l,width=.2):
  n=max(1,math.ceil(math.dist(a,z)/.04))
  return all(self.clear((a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n),l,width) for i in range(n+1))
 def portals(self,a,l,radius=4.,step=.2,vd=.8):
  candidates=[]
  for i in range(-int(radius/step),int(radius/step)+1):
   for j in range(-int(radius/step),int(radius/step)+1):
    if not i and not j:continue
    p=(round(a[0]+i*step,5),round(a[1]+j*step,5))
    if self.via_clear(p,vd):candidates.append((math.dist(a,p),p))
  for dist,p in sorted(candidates):
   dx,dy=p[0]-a[0],p[1]-a[1];sign=lambda v:1 if v>=0 else -1
   m=min(abs(dx),abs(dy));mid1=(a[0]+sign(dx)*(abs(dx)-m),a[1]+sign(dy)*(abs(dy)-m));mid2=(a[0]+sign(dx)*m,a[1]+sign(dy)*m)
   for route in [[a,mid1,p],[a,mid2,p],[a,(p[0],a[1]),p],[a,(a[0],p[1]),p]]:
    if all(self.line_clear(u,v,l) for u,v in zip(route,route[1:])):
     yield dist,p,route;break
