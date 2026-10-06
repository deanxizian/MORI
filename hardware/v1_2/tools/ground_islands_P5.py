import sys,json
import pcbnew as k
from layout_P5 import *
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));k.ZONE_FILLER(b).Fill(b.Zones());g=[];anchor=[]
for z in b.Zones():
 if z.GetIsRuleArea() or z.GetNetname()!='/GND':continue
 l=z.GetLayer();s=z.GetFilledPolysList(l)
 for i in range(s.OutlineCount()):g.append((z,l,s,i));anchor.append(False)
items=[t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and t.GetNetname()=='/GND']+[q for f in b.GetFootprints()for q in f.Pads()if q.GetNetname()=='/GND' and q.GetAttribute()==k.PAD_ATTRIB_PTH]
for idx,(z,l,s,i)in enumerate(g):
 for t in items:
  if t.IsOnLayer(l) and (s.Contains(t.GetPosition(),i) or t.GetEffectiveShape(l).Collide(s.Outline(i),mm(.005))):anchor[idx]=True;break
out=[]
for idx,(z,l,s,i)in enumerate(g):
 if anchor[idx]:continue
 bb=s.Outline(i).BBox();row=dict(zone=z.GetZoneName(),polygon=i,bounds=[k.ToMM(v)for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]],pads=[])
 for f in b.GetFootprints():
  for q in f.Pads():
   if q.GetNetname()=='/GND' and q.IsOnLayer(l)and(s.Contains(q.GetPosition(),i)or q.GetEffectiveShape(l).Collide(s.Outline(i),mm(.005))):row['pads'].append(f.GetReference()+'.'+q.GetNumber())
 out.append(row)
print(json.dumps(out,indent=2))
