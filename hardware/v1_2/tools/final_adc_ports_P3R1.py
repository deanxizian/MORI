"""Reserve outward ADC resistor escapes; audited removal of small GND copper only."""
import json, math
import pcbnew as k
from layout_P3R1 import paths, xy, track, via, F, B
from geometry_guard_P3R1 import Guard, obstacles
_,_,p,r=paths('motion'); b=k.LoadBoard(str(p))
pads={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
jobs=[('R14',[(12.825,24.5),(14.3,24.5)]),
      ('R15',[(17.325,26),(17.8,25.525),(17.8,24.5)]),
      ('R16',[(19,24.675),(19,22.8)])]
log=[]
for ref,ps in jobs:
 q=pads[ref,'1']; net=q.GetNetname(); assert math.dist(xy(q.GetPosition()),ps[0])<.001
 bad=set()
 for l in [F,B]:bad.update(u for u,_ in obstacles(b,net,ps[-1],l,.8,True))
 for a,z in zip(ps,ps[1:]):
  n=max(1,math.ceil(math.dist(a,z)/.04))
  for i in range(n+1):bad.update(u for u,_ in obstacles(b,net,(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n),B,.2))
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()}
 hard=[u for u in bad if u not in ts or ts[u].GetNetname()!='/GND' or isinstance(ts[u],k.PCB_VIA) or k.ToMM(ts[u].GetWidth())>.4]
 if hard:print('BLOCKED',ref,hard,flush=True);continue
 removed=[{'uuid':u,'start':xy(ts[u].GetStart()),'end':xy(ts[u].GetEnd())} for u in bad]
 for u in bad:b.Delete(ts[u])
 track(b,net,ps,.2,B)
 if not any(isinstance(t,k.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),ps[-1])<.002 for t in b.GetTracks()):via(b,net,*ps[-1],grid=False)
 log.append(dict(ref=ref,net=net,route=ps,removed=removed));print(ref,net,ps,flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'final_adc_ports.json').write_text(json.dumps(log,indent=2)+'\n')
