"""Connect isolated SMD ground islands outward to a clear opposite ground pour."""
import sys,json,math
import pcbnew as k
from layout_P5 import *
from geometry_guard_P5 import Guard
from plane_finish_P5 import simple
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));k.ZONE_FILLER(b).Fill(b.Zones());zones={l:[z.GetFilledPolysList(l)for z in b.Zones()if not z.GetIsRuleArea()and z.GetNetname()=='/GND'and z.GetLayer()==l]for l in [F,B]};anchors=[t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and t.GetNetname()=='/GND']+[q for f in b.GetFootprints()for q in f.Pads()if q.GetNetname()=='/GND'and q.GetAttribute()==k.PAD_ATTRIB_PTH];islands=[]
for l,zs in zones.items():
 for s in zs:
  for i in range(s.OutlineCount()):
   if any(t.IsOnLayer(l)and(s.Contains(t.GetPosition(),i)or t.GetEffectiveShape(l).Collide(s.Outline(i),mm(.005)))for t in anchors):continue
   pads=[(f,q)for f in b.GetFootprints()for q in f.Pads()if q.GetNetname()=='/GND'and q.IsOnLayer(l)and(s.Contains(q.GetPosition(),i)or q.GetEffectiveShape(l).Collide(s.Outline(i),mm(.005)))]
   if pads:islands.append((l,pads))
log=[]
for l,pads in islands:
 other=B if l==F else F;g=Guard(b,'/GND');best=None
 for f,q in pads:
  a=xy(q.GetPosition())
  for dist,v,ps in g.portals(a,l,radius=4,step=.2,vd=.6):
   if not any(s.Contains(pt(*v))for s in zones[other]):continue
   cost=sum(math.dist(u,z)for u,z in zip(ps,ps[1:]))
   if best is None or cost<best[0]:best=(cost,v,ps,f.GetReference(),q.GetNumber())
   break
 if best is None:print('GND BLOCKED',[f.GetReference()+'.'+q.GetNumber()for f,q in pads],flush=True);continue
 cost,v,ps,ref,pin=best;track(b,'/GND',ps,.2,l);via(b,'/GND',*v,vd=.6,dr=.3,grid=False);row=dict(ref=ref,pin=pin,path=ps,via=v,layer=l);log.append(row);print('GND',ref,pin,ps,flush=True)
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
k.SaveBoard(str(p),b);(r/'ground_returns.json').write_text(json.dumps(log,indent=2)+'\n')
