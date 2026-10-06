"""Reserve local signal/power escape ports before routing longer buses."""
import json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,setplace,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};f=fps['R13'];old=(*xy(f.GetPosition()),f.GetOrientationDegrees())
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA):continue
 if any(t.GetNetCode()==q.GetNetCode() and t.IsOnLayer(B) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.001)) for q in f.Pads()):b.Delete(t)
setplace(f,51.5,24.5,180,'B')
for t in list(b.GetTracks()):
 if any(t.IsOnLayer(B) and (isinstance(t,k.PCB_VIA) or t.GetNetCode()!=q.GetNetCode()) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.205)) for q in f.Pads()):b.Delete(t)
create(b)
log=[]
jobs=[('/ARM_FEEDBACK',[(40.5,19.675),(40.5,18.1)]),('/+3V3',[(41.5,24.175),(41.5,22.7)]),('/IMU_CS',[(52.325,24.5),(53.9,24.5)]),('/+3V3',[(50.675,24.5),(49.9,24.5),(49.9,23.4)]),('/GND',[(35.45,11.75),(34.65,11.75),(34.65,13.2)])]
for net,ps in jobs:
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()};remove=set();blocked=[]
 for a,z in zip(ps,ps[1:]):
  for i in range(101):
   point=(a[0]+(z[0]-a[0])*i/100,a[1]+(z[1]-a[1])*i/100)
   for uid,info in obstacles(b,net,point,B):
    if uid in ts:remove.add(uid)
    else:blocked.append((uid,info))
 for l in [F,B]:
  for uid,info in obstacles(b,net,ps[-1],l,.8,True):
   if uid in ts:remove.add(uid)
   else:blocked.append((uid,info))
 if blocked:log.append(dict(net=net,points=ps,status='BLOCKED',obstacles=blocked));print('blocked local port',net,set(blocked),flush=True);continue
 for uid in remove:b.Delete(ts[uid])
 track(b,net,ps,.2,B)
 if not any(isinstance(t,k.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),ps[-1])<.01 for t in b.GetTracks()):via(b,net,*ps[-1],grid=False)
 log.append(dict(net=net,points=ps,status='ROUTED',removed=sorted(remove)))
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'local_reserved_ports.json').write_text(json.dumps(dict(R13_before=old,R13_after=[51.5,24.5,180],ports=log),ensure_ascii=False,indent=2)+'\n')
