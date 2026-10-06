"""Audit native power connectivity after excluding signal-width copper.

This verifies a drawn load path, not ampacity or thermal qualification.
Pads and vias are electrical junctions; IC internal conduction is NOT inferred.
"""
import json,math,collections,hashlib
import pcbnew as k
from helpers_P4 import paths
from layout_P3R1 import xy,F,B
_,d,p,r=paths('power');b=k.LoadBoard(str(p));rows=[]
def find(ref,net):return next(q for f in b.GetFootprints() if f.GetReference()==ref for q in f.Pads() if q.GetNetname()==net)
jobs=[('PACK_FUSED','J1',['Q90'],.5),('BAT_IN','Q90',['Q1'],.5),('BAT_REV','Q1',['R2'],.5),('BAT_MON','R2',['J2','J4','J6','F60','F70'],.5),('W9_IN','J3',['D10'],.5),('W_PRE','D10',['Q10'],.5),('W_VM','Q10',['C10','J7','J8','J11'],.5),('H6_IN','J5',['D30'],.5),('H_PRE','D30',['Q30'],.5),('H_VM','Q30',['C30','J9','J12'],.5),('W_DUMP_D','Q20',['J11'],.5),('H_DUMP_D','Q40',['J12'],.5),('+5V_MOTION','L60',['J17'],.5),('+5V_CAM','L70',['J18'],.5),('M5_VIN','F60',['U60'],.4),('C5_VIN','F70',['U70'],.4),('M5_SW','U60',['L60'],.4),('C5_SW','U70',['L70'],.4)]
for nn,sref,drefs,minw in jobs:
 net='/'+nn;items=[q for f in b.GetFootprints() for q in f.Pads() if q.GetNetname()==net]
 items += [t for t in b.GetTracks() if t.GetNetname()==net and (t.Type()==k.PCB_VIA_T or k.ToMM(t.GetWidth())>=minw-1e-6)]
 sh=[{l:t.GetEffectiveShape(l) for l in [F,B] if t.IsOnLayer(l)} for t in items];ids={t.m_Uuid.AsString():i for i,t in enumerate(items)};adj=collections.defaultdict(list)
 for i in range(len(items)):
  for j in range(i):
   if any(l in sh[j] and s.BBox().Intersects(sh[j][l].BBox()) and s.Collide(sh[j][l],0) for l,s in sh[i].items()):adj[i].append(j);adj[j].append(i)
 try:source=find(sref,net);start=ids[source.m_Uuid.AsString()]
 except StopIteration:rows.append(dict(net=net,status='FAIL',reason='source pad absent',ref=sref));continue
 prev={start:None};q=collections.deque([start])
 while q:
  i=q.popleft()
  for j in adj[i]:
   if j not in prev:prev[j]=i;q.append(j)
 for ref in drefs:
  dest=find(ref,net);goal=ids[dest.m_Uuid.AsString()];route=[];i=goal
  if goal in prev:
   while i is not None:route.append(items[i]);i=prev[i]
  widths=[k.ToMM(t.GetWidth()) for t in route if isinstance(t,k.PCB_TRACK) and t.Type()!=k.PCB_VIA_T]
  vias=[dict(xy_mm=xy(t.GetPosition()),drill_mm=k.ToMM(t.GetDrillValue())) for t in route if t.Type()==k.PCB_VIA_T]
  rows.append(dict(net=net,source=sref+'.'+source.GetNumber(),destination=ref+'.'+dest.GetNumber(),minimum_track_filter_mm=minw,status='PASS' if route else 'FAIL',route_minimum_track_width_mm=min(widths) if widths else None,route_vias=vias,route_uuids=[t.m_Uuid.AsString() for t in route]))
out=dict(pcb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),method='Native copper-shape adjacency after removing tracks narrower than the stated width; no internal IC conduction assumed',status='PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',does_not_validate='Copper temperature, current rating, via plating, zone-return bottlenecks, electrical transient or physical tests',rows=rows)
(r/'load_path_audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status']);print(json.dumps([x for x in rows if x['status']!='PASS'],indent=2))
