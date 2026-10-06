"""Simplify entire signal polylines between real terminals, not tiny segments.

No relocation of vias, pads, critical buck nodes, load conductors or ground.
The actual two-face component geometry and native DRC gate every change.
"""
from candidate import *
kind='power';p=PCB;r=R;b=load();cli=CLI
NETS={'/ARM_Q','/FAULT_N','/CHG_N','/BAT_ADC','/WHEEL_ADC','/CURRENT_ADC','/+5V_CAM','/M5_EN','/C5_EN'}
original=p.read_bytes();(r/'19_before_simplification.kicad_pcb').write_bytes(original)
log=[];tried=set();calls=0
def check():
 global calls
 k.SaveBoard(str(p),b);subprocess.run([cli,'pcb','drc','--format','json','--severity-all','--all-track-errors','--refill-zones','-o',str(r/'simplify-drc.json'),str(p)],capture_output=True,check=True);calls+=1
 return json.loads((r/'simplify-drc.json').read_text())
def bad(j):return collections.Counter(v['type']for v in j['violations']if v['type']not in['silk_over_copper','silk_overlap'])
cur=check()
for iteration in range(100):
 connected(b);alltracks=list(b.GetTracks());nodes=collections.defaultdict(list);eligible=[]
 for t in alltracks:
  if t.GetNetname() not in NETS or isinstance(t,k.PCB_VIA)or k.ToMM(t.GetWidth())>.21 or t.GetNetname()in['/GND','/M5_FB','/C5_FB','/M5_BOOT','/C5_BOOT','/M5_SW','/C5_SW','/KELVIN_N','/KELVIN_P']:continue
  eligible.append(t)
  for v in [xy(t.GetStart()),xy(t.GetEnd())]:nodes[t.GetNetname(),t.GetLayer(),v].append(t)
 def anchor(net,l,v):
  if len(nodes[net,l,v])!=2:return True
  if any(isinstance(t,k.PCB_VIA)and t.GetNetname()==net and math.dist(xy(t.GetPosition()),v)<.45 for t in alltracks):return True
  return any(q.GetNetname()==net and q.IsOnLayer(l)and q.GetEffectiveShape(l).Collide(pt(*v),mm(.01))for f in b.GetFootprints()for q in f.Pads())
 candidates=[];seen=set()
 for first in eligible:
  net,l=first.GetNetname(),first.GetLayer()
  for a in [xy(first.GetStart()),xy(first.GetEnd())]:
   if not anchor(net,l,a):continue
   ts=[];ps=[a];t=first;v=a
   while t.m_Uuid.AsString()not in {q.m_Uuid.AsString()for q in ts}:
    ts.append(t);z=xy(t.GetEnd())if xy(t.GetStart())==v else xy(t.GetStart());ps.append(z)
    if anchor(net,l,z):break
    nxt=[q for q in nodes[net,l,z]if q.m_Uuid.AsString()!=t.m_Uuid.AsString()]
    if len(nxt)!=1 or nxt[0].GetWidth()!=first.GetWidth():break
    t=nxt[0];v=z
   ids=tuple(sorted(t.m_Uuid.AsString()for t in ts))
   if len(ts)<3 or ids in seen:continue
   seen.add(ids);oldlen=sum(math.dist(x,y)for x,y in zip(ps,ps[1:]));w=k.ToMM(first.GetWidth());g=Guard(b,net)
   for new in simple(ps[0],ps[-1]):
    key=(ids,tuple(new))
    if key in tried or len(new)>=len(ps):continue
    newlen=sum(math.dist(x,y)for x,y in zip(new,new[1:]));gain=oldlen-newlen
    if gain<-.005 or (len(ps)-len(new)<2 and gain<.15):continue
    if all(g.line_clear(x,y,l,w)for x,y in zip(new,new[1:])):
     candidates.append((-gain-.3*(len(ps)-len(new)),key,ids,ps,new,net,l,w));break
 if not candidates:break
 _,key,ids,old,new,net,l,w=min(candidates,key=lambda q:q[0]);tried.add(key);before=p.read_bytes()
 for t in list(b.GetTracks()):
  if t.m_Uuid.AsString()in ids:b.Delete(t)
 track(b,net,new,w,l);nxt=check();aa,zz=bad(nxt),bad(cur)
 if len(nxt['unconnected_items'])<=len(cur['unconnected_items'])and all(aa[t]<=zz[t]for t in aa):
  log.append(dict(net=net,layer=b.GetLayerName(l),old=old,new=new,width_mm=w));cur=nxt;print(kind,'simplified',net,len(old)-1,'->',len(new)-1,flush=True)
 else:p.write_bytes(before);b=k.LoadBoard(str(p))
cur=check();(r/'19_simplify_drc.json').write_text(json.dumps(cur,ensure_ascii=False,indent=2)+'\n')
(r/'19_simplification.json').write_text(json.dumps(dict(changes=log,native_drc_calls=calls),indent=2)+'\n')
print(kind,len(log),'corridors simplified; native',bad(cur),'opens',len(cur['unconnected_items']),flush=True)
