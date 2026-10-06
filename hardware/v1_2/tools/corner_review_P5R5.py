"""Audit and apply the source R14 0.499999 mm bevel to free 90-degree elbows.

Pad/via landings and true T junctions are reported separately, not silently
relabelled as compliant bevels. Native DRC gates the batch.
"""
import sys,math,json,collections,subprocess
import pcbnew as k
from layout_P5 import *
from review_P5R5 import paths
from close_P5 import connected
from geometry_guard_P5 import Guard
kind=sys.argv[1];apply='--apply'in sys.argv;name,d,p,r=paths(kind);b=k.LoadBoard(str(p));connected(b);original=p.read_bytes();nodes=collections.defaultdict(list);alltracks=list(b.GetTracks());records=[];changes=[];used=set()
for t in alltracks:
 if isinstance(t,k.PCB_VIA):continue
 for v in [xy(t.GetStart()),xy(t.GetEnd())]:nodes[t.GetNetname(),t.GetLayer(),v].append(t)
for (net,l,v),ts in nodes.items():
 if len(ts)!=2 or ts[0].GetWidth()!=ts[1].GetWidth():continue
 a=xy(ts[0].GetEnd())if xy(ts[0].GetStart())==v else xy(ts[0].GetStart());z=xy(ts[1].GetEnd())if xy(ts[1].GetStart())==v else xy(ts[1].GetStart());la,lz=math.dist(a,v),math.dist(z,v)
 if min(la,lz)<.0001:continue
 dot=sum((u-w)*(t-w) for u,t,w in zip(a,z,v))/(la*lz)
 if abs(dot)>.0001:continue
 rec=dict(net=net,layer=b.GetLayerName(l),vertex=v,adjacent_lengths=[la,lz],status='NOT_TESTED')
 if any(q.GetEffectiveShape(l).Collide(pt(*v),mm(.02)) for f in b.GetFootprints()for q in f.Pads()if q.IsOnLayer(l)):
  rec.update(status='NOT_APPLICABLE',reason='Inside pad land; terminal geometry, not a free trace elbow');records.append(rec);continue
 if any((isinstance(t,k.PCB_VIA) or t not in ts)and t.GetNetname()==net and t.IsOnLayer(l)and t.GetEffectiveShape(l).Collide(pt(*v),mm(.002))for t in alltracks):
  rec.update(status='NOT_APPLICABLE',reason='Via landing or branch junction; keep physical connection');records.append(rec);continue
 if min(la,lz)<.500001:
  rec.update(status='FAIL',reason='Insufficient straight leg for exact source setback; review adjacent placement/escape');records.append(rec);continue
 x=tuple(v[i]+(a[i]-v[i])*.499999/la for i in range(2));y=tuple(v[i]+(z[i]-v[i])*.499999/lz for i in range(2));ps=[a,x,y,z];w=k.ToMM(ts[0].GetWidth());g=Guard(b,net)
 if not all(g.line_clear(u,t,l,w)for u,t in zip(ps,ps[1:])):
  rec.update(status='FAIL',reason='Exact bevel conflicts with clearance/body protection');records.append(rec);continue
 # A bevel may remove contact where a pad touches the side of a trace.
 candidates=[]
 for aa,zz in zip(ps,ps[1:]):
  tr=k.PCB_TRACK(b);tr.SetStart(pt(*aa));tr.SetEnd(pt(*zz));tr.SetWidth(mm(w));tr.SetLayer(l);candidates.append(tr)
 lost=[]
 for f in b.GetFootprints():
  for pd in f.Pads():
   if pd.GetNetname()!=net or not pd.IsOnLayer(l):continue
   shape=pd.GetEffectiveShape(l)
   if any(shape.Collide(t.GetEffectiveShape(l),0)for t in ts)and not any(shape.Collide(t.GetEffectiveShape(l),0)for t in candidates):lost.append(f.GetReference()+'.'+pd.GetNumber())
 if lost:
  rec.update(status='NOT_APPLICABLE',reason='Preserve native pad side-entry contact: '+','.join(lost));records.append(rec);continue
 if apply and not any(t.m_Uuid.AsString()in used for t in ts):
  for t in ts:used.add(t.m_Uuid.AsString());b.Remove(t)
  track(b,net,ps,w,l);changes.append(dict(**rec,new_path=ps,setback=.499999));rec.update(status='PASS',reason='Applied exact source setback; native batch check pending')
 else:rec.update(status='PASS',reason='Exact source setback geometry is feasible')
 records.append(rec)
if apply and changes:
 k.SaveBoard(str(r/'before_R14_bevel.kicad_pcb'),k.LoadBoard(str(p)));k.SaveBoard(str(p),b)
 cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli';subprocess.run([cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','-o',str(r/'R14-drc.json'),str(p)],check=True,capture_output=True)
 check=json.loads((r/'R14-drc.json').read_text());before=json.loads((r/'drc.json').read_text());types=lambda j:collections.Counter(v['type']for v in j['violations']if v['type']not in['silk_over_copper','silk_overlap','track_angle','track_dangling','via_dangling']);new=types(check);old=types(before)
 if len(check['unconnected_items'])>len(before['unconnected_items'])or any(new[t]>old[t]for t in new):
  p.write_bytes(original);print('R14 batch rejected; source restored',new,flush=True);changes=[]
 else:print('R14 batch native accepted',len(changes),flush=True)
 # Delete detached SWIG items after the final native file has been saved.
 for t in alltracks:
  if t.m_Uuid.AsString()in used:b.Add(t);b.Delete(t)
(r/'R14_corner_review.json').write_text(json.dumps(dict(applied=changes,corner_review=records,scope='90-degree free elbows; existing deliberate diagonal runs and electrical branch T junctions are separate geometry',full_R14_equivalence='NOT_TESTED'),indent=2)+'\n');print(kind,'90-degree cases',len(records),'free-fail',sum(v['status']=='FAIL'for v in records),'applied',len(changes))
