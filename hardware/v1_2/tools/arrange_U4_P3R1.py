"""Compare and apply a complete U4 fanout, with decoupling facing VCCA.

R1 moves left, C4 rotates and moves to the right supply side, and R9 moves
below the level shifter. Each pin escapes outward before any layer change.
"""
import json,math
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,setplace,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};moves=[];removed=[];log=[]
for ref,pos in [('R1',(31.5,10.075,90)),('C4',(40.7,8.5,90)),('R9',(42,14,0))]:
 f=fps[ref];old=(*xy(f.GetPosition()),f.GetOrientationDegrees())
 for t in list(b.GetTracks()):
  if isinstance(t,k.PCB_VIA):continue
  if any(t.GetNetCode()==q.GetNetCode() and t.IsOnLayer(B) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.001)) for q in f.Pads()):removed.append(t.m_Uuid.AsString());b.Delete(t)
 setplace(f,*pos,'B');moves.append(dict(ref=ref,before=old,after=pos))
 for t in list(b.GetTracks()):
  if any(t.IsOnLayer(B) and (isinstance(t,k.PCB_VIA) or t.GetNetCode()!=q.GetNetCode()) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.205)) for q in f.Pads()):removed.append(t.m_Uuid.AsString());b.Delete(t)
create(b)
# Remove only previous U4 escape copper; leave the neighbouring U1 fanout.
f=fps['U4']
for t in list(b.GetTracks()):
 if not isinstance(t,k.PCB_VIA) and any(t.GetNetCode()==q.GetNetCode() and t.IsOnLayer(B) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.001)) for q in f.Pads()):removed.append(t.m_Uuid.AsString());b.Delete(t)
jobs=[
 ('/LINK_RX',[(35.45,10.75),(34.6,10.75),(34.6,8)],True),
 ('/+3V3',[(35.45,11.25),(33.85,11.25),(33.85,10.55)],True),
 ('/GND',[(35.45,11.75),(33,11.75)],True),
 ('/CAM_TX',[(35.45,12.25),(34.6,12.25),(34.1,12.75),(34.1,13.5)],True),
 ('/LINK_TX',[(38.55,10.75),(39,10.75),(39,8)],True),
 ('/+3V3',[(38.55,11.25),(39.5,11.25),(40.7,10.05),(40.7,9.275)],False),
 ('/+3V3',[(40.7,10.05),(41.45,10.8),(41.8,10.8)],True),
 ('/CAM_3V3',[(38.55,11.75),(40.8,11.75)],True),
 ('/CAM_RX_BUF',[(38.55,12.25),(39.3,12.25),(39.3,14),(41.175,14)],False),
 ('/CAM_3V3',[(38.275,14),(38.85,14),(38.85,15.25)],True),
 ('/CAM_RX',[(42.825,14),(44.3,14)],True)]
for net,ps,want_via in jobs:
 ts={t.m_Uuid.AsString():t for t in b.GetTracks()};bad=set();blocked=[]
 for a,z in zip(ps,ps[1:]):
  for i in range(121):
   point=(a[0]+(z[0]-a[0])*i/120,a[1]+(z[1]-a[1])*i/120)
   for uid,info in obstacles(b,net,point,B):
    if uid in ts:bad.add(uid)
    else:blocked.append((uid,info))
 if want_via:
  for l in [F,B]:
   for uid,info in obstacles(b,net,ps[-1],l,.8,True):
    if uid in ts:bad.add(uid)
    else:blocked.append((uid,info))
 if blocked:log.append(dict(net=net,points=ps,status='BLOCKED',obstacles=sorted(set(blocked))));print('BLOCKED U4',net,sorted(set(blocked)),flush=True);continue
 for uid in bad:removed.append(uid);b.Delete(ts[uid])
 track(b,net,ps,.2,B)
 if want_via and not any(isinstance(t,k.PCB_VIA) and t.GetNetname()==net and math.dist(xy(t.GetPosition()),ps[-1])<.01 for t in b.GetTracks()):via(b,net,*ps[-1],grid=False)
 log.append(dict(net=net,points=ps,status='ROUTED'))
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'U4_group_placement.json').write_text(json.dumps(dict(moves=moves,ports=log,removed=removed),ensure_ascii=False,indent=2)+'\n')
