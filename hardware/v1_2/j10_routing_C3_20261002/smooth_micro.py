"""Remove small interior grid detours; retain real pad/via/branch terminals."""
from candidate import *
import collections
nets={'/ARM_Q','/FAULT_N','/CHG_N','/BAT_ADC','/WHEEL_ADC','/CURRENT_ADC','/+5V_CAM','/M5_EN','/C5_EN','/BAT_MON','/H_PRE','/H6_IN','/C5_VIN'}
b=load();log=[];tried=set();baseline=check('36_before')
def test():
 save(b);args=[CLI,'pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','-o',str(R/'36_trial_drc.json'),str(PCB)];c=subprocess.run(args,capture_output=True,text=True);return json.loads((R/'36_trial_drc.json').read_text())
for iteration in range(40):
 nodes=collections.defaultdict(list)
 for t in b.GetTracks():
  if isinstance(t,k.PCB_VIA)or t.GetNetname()not in nets:continue
  for p in [xy(t.GetStart()),xy(t.GetEnd())]:nodes[t.GetNetname(),t.GetLayer(),p].append(t)
 def terminal(n,l,p):
  return any(isinstance(t,k.PCB_VIA)and t.GetNetname()==n and math.dist(xy(t.GetPosition()),p)<.01 for t in b.GetTracks())or any(q.GetNetname()==n and q.IsOnLayer(l)and q.GetEffectiveShape(l).Collide(pt(*p),0)for f in b.GetFootprints()for q in f.Pads())
 changed=False
 for mid in list(b.GetTracks()):
  if isinstance(mid,k.PCB_VIA)or mid.GetNetname()not in nets:continue
  u,v=xy(mid.GetStart()),xy(mid.GetEnd());n,l=mid.GetNetname(),mid.GetLayer();w=k.ToMM(mid.GetWidth())
  if math.dist(u,v)>.251 or terminal(n,l,u)or terminal(n,l,v):continue
  aa=nodes[n,l,u];zz=nodes[n,l,v]
  if len(aa)!=2 or len(zz)!=2:continue
  ta=next(t for t in aa if t.m_Uuid.AsString()!=mid.m_Uuid.AsString());tz=next(t for t in zz if t.m_Uuid.AsString()!=mid.m_Uuid.AsString())
  if ta.GetWidth()!=mid.GetWidth()or tz.GetWidth()!=mid.GetWidth():continue
  a=xy(ta.GetEnd())if xy(ta.GetStart())==u else xy(ta.GetStart());z=xy(tz.GetEnd())if xy(tz.GetStart())==v else xy(tz.GetStart());ids=tuple(sorted(t.m_Uuid.AsString()for t in [ta,mid,tz]));g=Guard(b,n)
  # Prefer a longer deliberate 45-degree corner; use straight when the three
  # original segments form a sub-grid lateral offset between fixed terminals.
  choices=simple(a,z)+[[a,z]];attempt=False
  for pts in choices:
   key=(ids,tuple(pts))
   if key in tried:continue
   tried.add(key)
   if not all(g.line_clear(x,y,l,w)for x,y in zip(pts,pts[1:])):continue
   attempt=True;oldbytes=PCB.read_bytes();oldpts=[a,u,v,z]
   for t in [ta,mid,tz]:b.Delete(t)
   track(b,n,pts,w,l);j=test()
   if not j['violations']and not j['unconnected_items']and not j['schematic_parity']:
    log.append({'net':n,'layer':b.GetLayerName(l),'width':w,'old':oldpts,'new':pts});print('SMOOTH',n,oldpts,'->',pts,flush=True);changed=True
   else:PCB.write_bytes(oldbytes);b=load()
   break
  if attempt:break
 if not changed:
  # Remaining candidates may have been rejected; keep bounded retry loop.
  if iteration>=20:break
save(b);dump(R/'36_smoothing.json',log);check('36_smooth');snapshot('36_smooth')
