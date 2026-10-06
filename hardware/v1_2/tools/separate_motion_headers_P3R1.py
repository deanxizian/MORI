"""Separate back-side J6 from the outward fanout of front-side J7."""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,setplace,track,via,F,B,mm
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard,obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
# Remove the failed staggered 3V3 escape only, retaining the main rail.
pad=next(q for q in fps['J7'].Pads() if q.GetNumber()=='1');c=b.GetConnectivity();c.Build(b);seen=set();todo=[pad];remove=set()
while todo:
 u=todo.pop();uid=u.m_Uuid.AsString()
 if uid in seen:continue
 seen.add(uid)
 for t in c.GetConnectedTracks(u):
  if t.GetNetname()=='/+3V3':remove.add(t.m_Uuid.AsString());todo.append(t)
ts={t.m_Uuid.AsString():t for t in b.GetTracks()}
assert len(remove)<12,('unexpected main-rail connectivity',len(remove))
for uid in remove:b.Delete(ts[uid])
f=fps['J6'];old=xy(f.GetPosition())
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA):continue
 if any(q.GetNetCode()==t.GetNetCode() and q.IsOnLayer(t.GetLayer()) and t.GetEffectiveShape(t.GetLayer()).Collide(q.GetEffectiveShape(t.GetLayer()),mm(.001)) for q in f.Pads()):b.Delete(t)
setplace(f,64,22,0,'B');zones=create(b)
# A legacy HEAD_BUS diagonal ran through the proposed 3V3 via location.
bad={uid for ll in [F,B] for uid,net in obstacles(b,'/+3V3',(61.375,26.8),ll,.8,True)}
ts={t.m_Uuid.AsString():t for t in b.GetTracks()}
for uid in bad:
 assert uid in ts and ts[uid].GetNetname()=='/HEAD_BUS' and k.ToMM(ts[uid].GetWidth())<=.2
 b.Delete(ts[uid])
for net,x in [('/+3V3',61.375),('/ARM_Q',60.125)]:
 assert Guard(b,net).line_clear((x,28.3),(x,26.8),F)
 track(b,net,[(x,28.3),(x,26.8)],.2,F)
 if not any(isinstance(t,k.PCB_VIA) and t.GetNetname()==net and xy(t.GetPosition())==(x,26.8) for t in b.GetTracks()):
  assert Guard(b,net).via_clear((x,26.8));via(b,net,x,26.8,grid=False)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,indent=2)+'\n')
(r/'header_separation.json').write_text(json.dumps(dict(J6_old=old,J6_new=[64,22],rotation_deg=0,reason='Back-side housing/mount pad previously blocked the front J7 3V3 outward via; translate the connector3mm to provide a clear corridor.',mating_access='BLOCKED pending mechanical review',displaced_HEAD_BUS=sorted(bad)),indent=2)+'\n')
print('J6 translated3mm; J7 outward3V3/ARM escapes separated')
