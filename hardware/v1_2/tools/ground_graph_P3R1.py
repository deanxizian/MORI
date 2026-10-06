"""Read-only geometry diagnostic for connected ground regions."""
import pcbnew as k,sys,json
from layout_P3R1 import paths,xy,F,B,mm
kind=sys.argv[1];_,d,p,r=paths(kind);b=k.LoadBoard(str(p));items=[];parent=[];ids={}
def add(label,shape,layer,link,at):
 i=len(items);items.append((label,shape,layer,at));parent.append(i)
 if link in ids:union(i,ids[link])
 else:ids[link]=i
 return i
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def union(i,j):parent[root(j)]=root(i)
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetNetname()!='/GND':continue
  for l in [F,B]:
   if q.IsOnLayer(l):add(f.GetReference()+'.'+q.GetNumber(),q.GetEffectiveShape(l),l,q.m_Uuid.AsString(),xy(q.GetPosition()))
for t in b.GetTracks():
 if t.GetNetname()!='/GND':continue
 for l in [F,B]:
  if t.IsOnLayer(l):add(('VIA' if isinstance(t,k.PCB_VIA) else 'TRACK')+' '+t.m_Uuid.AsString(),t.GetEffectiveShape(l),l,t.m_Uuid.AsString(),xy(t.GetPosition()))
for z in b.Zones():
 if z.GetIsRuleArea() or z.GetNetname()!='/GND':continue
 sh=z.GetFilledPolysList(z.GetLayer())
 for i in range(sh.OutlineCount()):
  sub=sh.Subset(i,i+1);bb=sub.BBox();add(z.GetZoneName()+'['+str(i)+']',sub,z.GetLayer(),z.m_Uuid.AsString()+str(i),[k.ToMM(bb.GetX()),k.ToMM(bb.GetY())])
for i,a in enumerate(items):
 for j in range(i):
  z=items[j]
  if a[2]!=z[2] or root(i)==root(j) or not a[1].BBox().Intersects(z[1].BBox()):continue
  if a[1].Collide(z[1],mm(.002)):union(i,j)
groups={}
for i,(label,shape,layer,at) in enumerate(items):groups.setdefault(root(i),[]).append(dict(label=label,layer=k.LayerName(layer),at=at))
groups=sorted(groups.values(),key=len,reverse=True);(r/'ground_components.json').write_text(json.dumps(groups,indent=2)+'\n')
for group in groups:
 print('component',len(group),[x for x in group if not x['label'].startswith(('TRACK','VIA'))],flush=True)
