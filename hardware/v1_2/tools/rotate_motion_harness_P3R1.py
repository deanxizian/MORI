"""Rotate J7 so pin tails face the interior routing space.

The pin identity stays unchanged; mating orientation changes and must be
included in the mechanical/harness handoff. This opens the MCU-to-power nets.
"""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,setplace,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard,obstacles
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));f=next(f for f in b.GetFootprints() if f.GetReference()=='J7');nets={q.GetNetname() for q in f.Pads() if q.GetNetname()};old=(*xy(f.GetPosition()),f.GetOrientationDegrees());removed=[]
oldports=json.loads((r/'connector_escapes.json').read_text());positions=[q['outward_via_mm'] for q in oldports if q['ref']=='J7' and q['status']=='ROUTED']
for t in list(b.GetTracks()):
 kill=False
 if isinstance(t,k.PCB_VIA):kill=any(__import__('math').dist(xy(t.GetPosition()),q)<.01 for q in positions)
 elif t.GetNetname() in nets and t.GetLayer()==F:
  a,z=xy(t.GetStart()),xy(t.GetEnd());kill=49<a[0]<65 and 26<a[1]<35 and 49<z[0]<65 and 26<z[1]<35
 if kill:removed.append(t.m_Uuid.AsString());b.Delete(t)
setplace(f,57,30.25,180,'F');create(b)
# Relocation invalidates copper underneath new pad locations.
for t in list(b.GetTracks()):
 if any(t.IsOnLayer(F) and (isinstance(t,k.PCB_VIA) or t.GetNetCode()!=q.GetNetCode()) and t.GetEffectiveShape(F).Collide(q.GetEffectiveShape(F),mm(.205)) for q in f.Pads()):removed.append(t.m_Uuid.AsString());b.Delete(t)
for q in f.Pads():
 if not q.GetNumber().isdigit() or q.GetNetname()=='/GND':continue
 a=xy(q.GetPosition());z=(a[0],26.8);net=q.GetNetname();bad=set();ts={t.m_Uuid.AsString():t for t in b.GetTracks()}
 for i in range(101):
  pp=(a[0],a[1]+(z[1]-a[1])*i/100)
  for uid,info in obstacles(b,net,pp,F):
   assert uid in ts,(net,uid,info);bad.add(uid)
 for uid in bad:removed.append(uid);b.Delete(ts[uid])
 track(b,net,[a,z],.2,F)
# Explicit short decoupling supply path out of U4's upper-left pin.
net='/+3V3';points=[(35.45,11.25),(34.6,11.25),(34.6,9),(35.225,9)]
bad=set();ts={t.m_Uuid.AsString():t for t in b.GetTracks()}
for a,z in zip(points,points[1:]):
 for i in range(101):
  pp=(a[0]+(z[0]-a[0])*i/100,a[1]+(z[1]-a[1])*i/100)
  for uid,info in obstacles(b,net,pp,B):
   assert uid in ts,(net,uid,info);bad.add(uid)
for uid in bad:removed.append(uid);b.Delete(ts[uid])
track(b,net,points,.2,B)
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'J7_orientation_trial.json').write_text(json.dumps(dict(before=old,after=[57,30.25,180],reason='Pin tails face open interior copper; ADC pins now closer to the MCU side. Physical mating direction changes.',removed=removed),ensure_ascii=False,indent=2)+'\n')
print('J7 rotated; straight interior pin escapes reserved',flush=True)
