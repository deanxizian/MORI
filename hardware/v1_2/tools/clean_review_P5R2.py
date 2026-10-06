#!/usr/bin/env python3
"""Transactional geometric cleanup with a zero-error native gate per edit.

All widths/nets considered. Critical converter and Kelvin paths are not
globally rerouted here; only redundant copper is removed on those nets.
This tool is a review aid, not a substitute for the per-net visual review.
"""
import pcbnew as k
import math,json,collections,subprocess,sys,time
from all_trace_review_P5R2 import paths,CLI,xy,pt,mm,F,B,segment_distance
from layout_P5 import track
from close_P5 import connected
from geometry_guard_P5 import Guard
from plane_finish_P5 import simple
kind=sys.argv[1]; mode=sys.argv[2];name,d,p,r=paths(kind)
b=k.LoadBoard(str(p));connected(b);saved=r/(mode+'_transactions.json');prior=json.loads(saved.read_text())if saved.exists()else{};log=prior.get('edits',[]);calls=prior.get('native_calls',0)
if mode=='chains':
 raw_xy=xy
 xy=lambda v:tuple(round(q,4)for q in raw_xy(v))
critical={'/M5_SW','/C5_SW','/M5_FB','/C5_FB','/M5_BOOT','/C5_BOOT','/M5_VIN','/C5_VIN','/KELVIN_N','/KELVIN_P'}
def check():
 global calls
 k.SaveBoard(str(p),b);args=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','--exit-code-violations','-o',str(r/'candidate_drc.json'),str(p)]
 q=subprocess.run(args,capture_output=True,text=True);calls+=1;j=json.loads((r/'candidate_drc.json').read_text())
 return q.returncode==0 and not j['violations'] and not j['unconnected_items'],j
ok,j=check();assert ok,[(x['type'],x['description'])for x in j['violations']]
def commit(before,record):
 global b
 ok,j=check();record['accepted']=ok
 record['native_counts']={'violations':len(j['violations']),'unconnected':len(j['unconnected_items'])}
 if not ok:
  record['rejected_types']=dict(collections.Counter(x['type']for x in j['violations']));p.write_bytes(before);b=k.LoadBoard(str(p));connected(b)
 else:print(kind,mode,record.get('net'),record.get('reason'),flush=True)
 log.append(record);(r/(mode+'_transactions.json')).write_text(json.dumps({'native_calls':calls,'edits':log},indent=2)+'\n');return ok
def redundant():
 tested={u for e in log for u in e.get("removed",[])}
 while True:
  found=False;ts=[t for t in b.GetTracks()if not isinstance(t,k.PCB_VIA)]
  for t in sorted(ts,key=lambda t:k.ToMM(t.GetLength())):
   uid=t.m_Uuid.AsString()
   if uid in tested:continue
   net=t.GetNetname();l=t.GetLayer();a,z=xy(t.GetStart()),xy(t.GetEnd());w=k.ToMM(t.GetWidth())
   others=[u for u in ts if u!=t and u.GetNetname()==net and u.GetLayer()==l and u.GetWidth()>=t.GetWidth()]
   # Same-width overlapping centreline, or entire original conductor inside a wider one.
   padsh=[q.GetEffectiveShape(l)for f in b.GetFootprints()for q in f.Pads()if q.GetNetname()==net and q.IsOnLayer(l)]
   N=max(2,math.ceil(math.dist(a,z)/.05));points=[(a[0]+(z[0]-a[0])*i/N,a[1]+(z[1]-a[1])*i/N)for i in range(N+1)]
   covered=all(any(segment_distance(v,xy(u.GetStart()),xy(u.GetEnd())) <= max(.001,(k.ToMM(u.GetWidth())-w)/2)for u in others)or any(sh.Collide(pt(*v),0)for sh in padsh)for v in points)
   if not covered:continue
   tested.add(uid);before=p.read_bytes();rec={'net':net,'removed':[uid],'width_mm':w,'a':a,'z':z,'reason':'Contained redundant segment; existing equal/wider conductor or own pad retained'};b.Delete(t)
   commit(before,rec);found=True;break
  if not found:break
def chains():
 tried=set()
 for iteration in range(180):
  allts=list(b.GetTracks());ts=[t for t in allts if not isinstance(t,k.PCB_VIA)];nodes=collections.defaultdict(list)
  for t in ts:
   for v in [xy(t.GetStart()),xy(t.GetEnd())]:nodes[t.GetNetname(),t.GetLayer(),v].append(t)
  def anchor(net,l,v):
   if len(nodes[net,l,v])!=2:return True
   if any(isinstance(t,k.PCB_VIA)and t.GetNetname()==net and math.dist(xy(t.GetPosition()),v)<.42 for t in allts):return True
   return any(q.GetNetname()==net and q.IsOnLayer(l)and q.GetEffectiveShape(l).Collide(pt(*v),mm(.001))for f in b.GetFootprints()for q in f.Pads())
  candidates=[];seen=set();guards={}
  for first in ts:
   net,l=first.GetNetname(),first.GetLayer()
   if net in critical:continue
   for a in [xy(first.GetStart()),xy(first.GetEnd())]:
    if not anchor(net,l,a):continue
    seq=[];ps=[a];t=first;v=a
    while t.m_Uuid.AsString()not in {q.m_Uuid.AsString()for q in seq}:
     seq.append(t);z=xy(t.GetEnd())if xy(t.GetStart())==v else xy(t.GetStart());ps.append(z)
     if anchor(net,l,z):break
     nxt=[q for q in nodes[net,l,z]if q.m_Uuid.AsString()!=t.m_Uuid.AsString()]
     if len(nxt)!=1 or nxt[0].GetWidth()!=first.GetWidth():break
     t=nxt[0];v=z
    ids=tuple(sorted(t.m_Uuid.AsString()for t in seq))
    if len(seq)<2 or ids in seen:continue
    seen.add(ids);oldlen=sum(math.dist(x,y)for x,y in zip(ps,ps[1:]));w=k.ToMM(first.GetWidth())
    if net not in guards:guards[net]=Guard(b,net)
    g=guards[net]
    for new in simple(ps[0],ps[-1]):
     key=(ids,tuple(new))
     if key in tried or len(new)>len(ps):continue
     newlen=sum(math.dist(x,y)for x,y in zip(new,new[1:]));gain=oldlen-newlen
     if gain<-.00001 or(len(new)==len(ps)and gain<.2):continue
     if len(new)==len(ps)and new==ps:continue
     if all(g.line_clear(x,y,l,w)for x,y in zip(new,new[1:])):candidates.append((-gain-.2*(len(ps)-len(new)),key,ids,ps,new,net,l,w));break
  if not candidates:break
  _,key,ids,old,new,net,l,w=min(candidates,key=lambda q:q[0]);tried.add(key);before=p.read_bytes()
  for t in list(b.GetTracks()):
   if t.m_Uuid.AsString()in ids:b.Delete(t)
  added=track(b,net,new,w,l);commit(before,{'net':net,'layer':b.GetLayerName(l),'removed':ids,'added':[t.m_Uuid.AsString()for t in added],'old':old,'new':new,'width_mm':w,'reason':'Fewer bends / shorter whole corridor between unchanged terminals'})
if mode=='redundant':redundant()
elif mode=='chains':chains()
else:raise SystemExit(mode)
ok,j=check();assert ok
(r/(mode+'_transactions.json')).write_text(json.dumps({'native_calls':calls,'edits':log},indent=2)+'\n')
print(kind,mode,'accepted',sum(v['accepted']for v in log),'rejected',sum(not v['accepted']for v in log),flush=True)
