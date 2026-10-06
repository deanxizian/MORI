from candidate import *
b=load();k.ZONE_FILLER(b).Fill(b.Zones()); layers=[k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu];items=[];sh=[]
for f in b.GetFootprints():
 for p in f.Pads():
  if p.GetNetname()!='/GND':continue
  items.append(dict(kind='pad',id=f.GetReference()+'.'+p.GetNumber(),xy=xy(p.GetPosition())))
  sh.append({l:p.GetEffectiveShape(l)for l in layers if p.IsOnLayer(l)})
for t in b.GetTracks():
 if t.GetNetname()!='/GND':continue
 items.append(dict(kind='via'if isinstance(t,k.PCB_VIA)else'track',id=t.m_Uuid.AsString(),a=xy(t.GetStart()),z=xy(t.GetEnd())))
 sh.append({l:t.GetEffectiveShape(l)for l in layers if t.IsOnLayer(l)})
for z in b.Zones():
 if z.GetIsRuleArea()or z.GetNetname()!='/GND':continue
 for l in layers:
  if not z.IsOnLayer(l):continue
  poly=z.GetFilledPolysList(l)
  for i in range(poly.OutlineCount()):
   unit=poly.UnitSet(i);bb=unit.BBox();items.append(dict(kind='zone',id=z.GetZoneName()+':'+str(i),bbox=[k.ToMM(v)for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]));sh.append({l:unit})
adj=collections.defaultdict(list)
for i in range(len(items)):
 for j in range(i):
  if any(l in sh[j]and s.BBox().Intersects(sh[j][l].BBox())and s.Collide(sh[j][l],0)for l,s in sh[i].items()):adj[i].append(j);adj[j].append(i)
seen=set();cc=[]
for i in range(len(items)):
 if i in seen:continue
 todo=[i];island=[]
 while todo:
  j=todo.pop()
  if j in seen:continue
  seen.add(j);island.append(items[j]);todo.extend(adj[j])
 cc.append(island)
cc.sort(key=len,reverse=True);dump(R/'25_ground_graph.json',cc);print('ground clusters',[(len(x),x if len(x)<12 else x[:2])for x in cc],flush=True)
