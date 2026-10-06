"""Keep U4 ground escape clear of its lower signal pin, then reserve that pin."""
import json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,F,B
from geometry_guard_P3R1 import obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));removed=[]
for t in list(b.GetTracks()):
 if t.GetNetname()!='/GND':continue
 if isinstance(t,k.PCB_VIA):kill=math.dist(xy(t.GetPosition()),(34.65,13.2))<.01
 else:kill=(xy(t.GetStart()),xy(t.GetEnd())) in [((35.45,11.75),(34.65,11.75)),((34.65,11.75),(34.65,13.2))]
 if kill:removed.append(t.m_Uuid.AsString());b.Delete(t)
log=[]
for net,ps in [('/GND',[(35.45,11.75),(32,11.75)])]:
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()};bad=set();blocked=[]
 for a,z in zip(ps,ps[1:]):
  for i in range(101):
   point=(a[0]+(z[0]-a[0])*i/100,a[1]+(z[1]-a[1])*i/100)
   for uid,info in obstacles(b,net,point,B):
    if uid in ts:bad.add(uid)
    else:blocked.append((uid,info))
 for l in [F,B]:
  for uid,info in obstacles(b,net,ps[-1],l,.8,True):
   if uid in ts:bad.add(uid)
   else:blocked.append((uid,info))
 if blocked:print('BLOCKED',net,set(blocked));continue
 for uid in bad:b.Delete(ts[uid]);removed.append(uid)
 track(b,net,ps,.2,B);via(b,net,*ps[-1],grid=False);log.append(dict(net=net,path=ps))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'U4_ground_signal_escape.json').write_text(json.dumps(dict(routes=log,removed=removed),indent=2)+'\n')
