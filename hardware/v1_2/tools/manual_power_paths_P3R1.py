"""Deliberate wide paths after component rotations; preserve pad necks."""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,F,B
from geometry_guard_P3R1 import Guard,obstacles
name,d,p,r=paths('power');b=k.LoadBoard(str(p));removed=[];log=[]
# The old C5 feed crossed the now-forward-facing fuse input corridor.
# Remove only that obstructing copper; C5 is explicitly reconnected next.
points=[(33,31.6),(33,29.3),(35.5,29.3),(35.5,30.545)]
ids=set()
for a,z in zip(points,points[1:]):
 for i in range(101):
  pos=(a[0]+(z[0]-a[0])*i/100,a[1]+(z[1]-a[1])*i/100)
  for uid,net in obstacles(b,'/BAT_MON',pos,F,1):
   if net in ['/C5_VIN','/GND']:ids.add(uid)
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() in ids:removed.append(dict(net=t.GetNetname(),start=xy(t.GetStart()),end=xy(t.GetEnd())));b.Delete(t)
jobs=[('/BAT_MON',points,1,F),
('/+5V_MOTION',[(17.775,20),(15.5,20),(15.5,21.5)],.8,F),
('/+5V_MOTION',[(8.1,20.625),(8.975,21.5),(15.5,21.5)],.8,B),
('/H_DUMP_D',[(76,45),(76,47),(72.5,50.5),(65,50.5),(65,48)],1,B)]
for net,ps,w,l in jobs:
 g=Guard(b,net)
 if all(g.line_clear(a,z,l,w) for a,z in zip(ps,ps[1:])):
  track(b,net,ps,w,l);log.append(dict(net=net,points=ps,width=w,status='ROUTED'));print('manual',net,'ROUTED',flush=True)
 else:
  bad=[(a,z) for a,z in zip(ps,ps[1:]) if not g.line_clear(a,z,l,w)];log.append(dict(net=net,status='BLOCKED',segments=bad));print('manual BLOCKED',net,bad,flush=True)
if Guard(b,'/+5V_MOTION').via_clear((15.5,21.5),1):via(b,'/+5V_MOTION',15.5,21.5,vd=1,dr=.45,grid=False)
else:print('manual BLOCKED 5V via',flush=True)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'manual_load_paths.json').write_text(json.dumps(dict(routes=log,removed=removed),ensure_ascii=False,indent=2)+'\n')
