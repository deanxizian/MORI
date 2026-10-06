"""Reserve deliberately spaced outward header escapes after group placement."""
import sys,json,math
import pcbnew as k
from layout_P3R1 import paths,xy,track,via,F,B
from geometry_guard_P3R1 import obstacles,Guard
kind=sys.argv[1];name,d,p,r=paths(kind);b=k.LoadBoard(str(p));pads={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()};logs=[];protect=set()
critical={'/M5_FB','/C5_FB','/M5_SW','/C5_SW','/M5_BOOT','/C5_BOOT','/KELVIN_P','/KELVIN_N','/W_PRE','/W_VM','/H_PRE','/H_VM','/BAT_MON','/BAT_REV','/BAT_IN'}
if kind=='power':
 for t in list(b.GetTracks()):
  if t.GetNetname()=='/CURRENT_ADC':b.Delete(t)
jobs=[]
if kind=='motion':
 for pin in ['2','3','4','5','6','7']:
  q=pads['J7',pin];a=xy(q.GetPosition());jobs.append(('J7:'+pin,q,[a,(a[0],24.9)],F))
 for ref,pin,end,ll in [('J3','1',(56,19.25),F),('R8','1',(61.2,16.75),B),('R8','2',(65.8,16.75),B),('R13','1',(47,20.575),B),('R13','2',(47,16.425),B)]:
  q=pads[ref,pin];jobs.append((ref+':'+pin,q,[xy(q.GetPosition()),end],ll))
else:
 for pin in ['1','2','3','4','5','6','7']:
  q=pads['J10',pin];a=xy(q.GetPosition());jobs.append(('J10:'+pin,q,[a,(52.5,a[1])],F))
 q=pads['U1','1'];jobs.append(('U1:1',q,[xy(q.GetPosition()),(22.45,21.95),(20,24.4)],B))
for label,q,ps,l in jobs:
 net=q.GetNetname();bad=set();end=ps[-1]
 for ll in [F,B]:bad.update(uid for uid,_ in obstacles(b,net,end,ll,.8,True))
 for a,z in zip(ps,ps[1:]):
  n=max(1,math.ceil(math.dist(a,z)/.05))
  for i in range(n+1):bad.update(uid for uid,_ in obstacles(b,net,(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n),l,.2))
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()};hard=[]
 for uid in bad:
  t=ts.get(uid)
  if t is None or uid in protect or t.GetNetname() in critical or (isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth(F))>=.9) or (not isinstance(t,k.PCB_VIA) and k.ToMM(t.GetWidth())>.4):hard.append(uid)
 if hard:logs.append(dict(pin=label,status='BLOCKED',hard=hard));print('PORT BLOCKED',label,hard,flush=True);continue
 for uid in bad:b.Delete(ts[uid])
 before={t.m_Uuid.AsString() for t in b.GetTracks()};track(b,net,ps,.2,l)
 if not any(isinstance(t,k.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),end)<.002 for t in b.GetTracks()):via(b,net,*end,grid=False)
 protect|={t.m_Uuid.AsString() for t in b.GetTracks()}-before
 logs.append(dict(pin=label,status='ROUTED',route=ps,layer=k.LayerName(l),removed=sorted(bad)));print('OUTWARD PORT',label,net,ps,'displaced',len(bad),flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'straight_header_ports.json').write_text(json.dumps(logs,indent=2)+'\n')
