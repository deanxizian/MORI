#!/usr/bin/env python3
"""Extract actual supply paths. Resistance estimates are not ampacity ratings."""
import pcbnew as k
import collections,math,json,hashlib,heapq
from all_trace_review_P5R2 import paths,KINDS,F,B,xy
rho=1.724e-5 # ohm mm, same explicit engineering assumption as P4 calculations
jobs={
 'power':[('PACK_FUSED','J1','Q90',6.48,.59),('BAT_IN','Q90','Q1',6.48,.59),('BAT_REV','Q1','R2',6.48,.59),('BAT_MON','R2','J2',3.8,.59),('BAT_MON','R2','J4',1.6,.59),('BAT_MON','R2','F60',.55,.59),('BAT_MON','R2','F70',1.35,.59),('W9_IN','J3','D10',3.34,.59),('W_PRE','D10','Q10',3.34,.59),('W_VM','Q10','J7',3.34,.59),('W_VM','Q10','J8',3.34,.59),('H6_IN','J5','D30',2,.59),('H_PRE','D30','Q30',2,.59),('H_VM','Q30','J9',2,.59),('W_DUMP_D','Q20','J11',3,.59),('H_DUMP_D','Q40','J12',2,.59),('+5V_MOTION','L60','J17',.75,.59),('+5V_CAM','L70','J18',2,.59),('M5_VIN','F60','U60',.55,.59),('C5_VIN','F70','U70',1.35,.59),('M5_SW','U60','L60',.75,.59),('C5_SW','U70','L70',2,.59)],
 'motion':[('+5V_MOTION','J1','U100',.75,.49)],
 'rear':[('VBUS_RAW','USB1','F1',1,.49),('VBUS_FUSED','F1','J2',1,.59)],
 'imu':[('+3V3','J1','U1',.02,.19)]}
allout={}
for kind in KINDS:
 n,d,p,r=paths(kind);b=k.LoadBoard(str(p));foil=.07 if kind=='power'else.035;plating=.020
 widths=collections.defaultdict(lambda:collections.Counter());thin=[]
 for t in b.GetTracks():
  if not isinstance(t,k.PCB_VIA):widths[t.GetNetname()][k.ToMM(t.GetWidth())]+=1
 rows=[]
 for nn,src,dst,current,minw in jobs[kind]:
  net='/'+nn;items=[q for f in b.GetFootprints()for q in f.Pads()if q.GetNetname()==net]
  items += [t for t in b.GetTracks()if t.GetNetname()==net and(isinstance(t,k.PCB_VIA)or k.ToMM(t.GetWidth())>=minw)]
  shapes=[{l:t.GetEffectiveShape(l)for l in [F,B]if t.IsOnLayer(l)}for t in items];adj=collections.defaultdict(list)
  costs=[]
  for t in items:
   if isinstance(t,k.PCB_VIA):cost=rho*1.6/(math.pi*(k.ToMM(t.GetDrillValue())+plating)*plating)
   elif isinstance(t,k.PCB_TRACK):cost=rho*k.ToMM(t.GetLength())/(k.ToMM(t.GetWidth())*foil)
   else:cost=0
   costs.append(cost)
  for i in range(len(items)):
   for j in range(i):
    if any(l in shapes[j]and sh.BBox().Intersects(shapes[j][l].BBox())and sh.Collide(shapes[j][l],0)for l,sh in shapes[i].items()):adj[i].append(j);adj[j].append(i)
  sources=[i for i,t in enumerate(items)if isinstance(t,k.PAD)and t.GetParentFootprint().GetReference()==src];goals={i for i,t in enumerate(items)if isinstance(t,k.PAD)and t.GetParentFootprint().GetReference()==dst};queue=[(0,i)for i in sources];heapq.heapify(queue);dist={i:0 for i in sources};prev={i:None for i in sources};goal=None
  while queue:
   cost,i=heapq.heappop(queue)
   if cost>dist[i]:continue
   if i in goals:goal=i;break
   for j in adj[i]:
    nc=cost+costs[j]
    if nc<dist.get(j,float('inf')):dist[j]=nc;prev[j]=i;heapq.heappush(queue,(nc,j))
  route=[];i=goal
  while i is not None:route.append(items[i]);i=prev[i]
  trs=[t for t in route if isinstance(t,k.PCB_TRACK)and not isinstance(t,k.PCB_VIA)];vs=[t for t in route if isinstance(t,k.PCB_VIA)]
  res=dist[goal]if goal is not None else None
  # A resistance-selected route may prefer a short narrow spur even when a
  # wider complete route exists. Report the widest minimum path separately.
  widest=None
  thresholds=sorted({k.ToMM(t.GetWidth())for t in items if isinstance(t,k.PCB_TRACK)and not isinstance(t,k.PCB_VIA)},reverse=True)
  for threshold in thresholds:
   allowed={i for i,t in enumerate(items)if not isinstance(t,k.PCB_TRACK)or isinstance(t,k.PCB_VIA)or k.ToMM(t.GetWidth())>=threshold-1e-6}
   seen=set(sources);q=list(sources)
   while q:
    i=q.pop()
    for j in adj[i]:
     if j in allowed and j not in seen:seen.add(j);q.append(j)
   if seen&goals:widest=threshold;break
  rows.append({'net':net,'source':src,'destination':dst,'design_scenario_A':current,'load_path_status':'PASS'if goal is not None else'FAIL','minimum_width_filter_mm':minw,'minimum_path_width_mm':min(k.ToMM(t.GetWidth())for t in trs)if trs else None,'widest_complete_path_minimum_width_mm':widest,'complete_segment_length_mm':sum(k.ToMM(t.GetLength())for t in trs),'single_path_vias':[{'xy':xy(t.GetPosition()),'drill_mm':k.ToMM(t.GetDrillValue())}for t in vs],'conservative_complete_segment_path_R20_mohm':res*1000 if res is not None else None,'drop20_mV':res*current*1000 if res is not None else None,'loss20_W':res*current*current if res is not None else None,'path_uuids':[t.m_Uuid.AsString()for t in route]})
 out={'pcb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'native_width_inventory':{n:dict(w)for n,w in sorted(widths.items())},'foil_mm_assumed':foil,'via_plating_mm_assumed':plating,'scenario_source':'S3 logic budgets 0.75A / 2A; 30W/9V wheel and 12W/6V head; 6.48A aggregate. Branch BAT_MON values are conservative engineering scenarios, not measured simultaneous currents. Rear1A from P4 input limit. IMU20mA is an engineering allowance.','method':'Native copper-shape adjacency after filtering narrow tracks, shortest resistance-weighted single path; sums full segment lengths even at mid-segment junctions. No IC internal conduction inferred. Copper zones, parallel current sharing, contact/connector/pad resistance and return network excluded.','qualification':'NOT_TESTED: this is drawn-path and DC resistance estimation only. It does not establish allowable continuous current or temperature rise. Converter SW currents have ripple, so DC scenarios are not RMS loss qualifications.','paths':rows}
 (r/'width_review.json').write_text(json.dumps(out,indent=2)+'\n');allout[kind]={'paths':len(rows),'fail':sum(q['load_path_status']!='PASS'for q in rows)}
 print(kind,allout[kind],flush=True)
