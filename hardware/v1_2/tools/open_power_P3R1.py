"""Reorient the lower fuse and bulk input capacitor; open the shunt corridor."""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,setplace,bounds,intersects,F,B
from geometry_guard_P3R1 import Guard
from body_keepouts_P3R1 import create
name,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};moves=[];removed=[]
for ref,pos in [('D1',(18,22,180)),('F70',(35.5,33,270)),('C76',(20,49.5,180))]:
 f=fps[ref];old=(*xy(f.GetPosition()),f.GetOrientationDegrees());side='B' if f.IsFlipped() else 'F'
 for t in list(b.GetTracks()):
  if isinstance(t,k.PCB_VIA):continue
  if any(t.GetNetCode()==pad.GetNetCode() and t.IsOnLayer(f.GetLayer()) and t.GetEffectiveShape(f.GetLayer()).Collide(pad.GetEffectiveShape(f.GetLayer()),mm(.001)) for pad in f.Pads()):
   removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),width=k.ToMM(t.GetWidth())));b.Delete(t)
 setplace(f,*pos,side);box=bounds(f)
 assert not any(q!=f and q.GetLayer()==f.GetLayer() and intersects(box,bounds(q),.12) for q in fps.values()),ref
 moves.append(dict(reference=ref,before=old,after=pos))
 for t in list(b.GetTracks()):
  if any(t.IsOnLayer(f.GetLayer()) and (isinstance(t,k.PCB_VIA) or t.GetNetCode()!=pad.GetNetCode()) and t.GetEffectiveShape(f.GetLayer()).Collide(pad.GetEffectiveShape(f.GetLayer()),mm(.205)) for pad in f.Pads()):
   removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname()));b.Delete(t)
create(b)
# Pad-size transitions at the shunt and 1.25 mm logic-power connector.
# Main battery paths retain 2 mm after these 1.24 mm-long pad necks.
for net,points,w,l in [('/BAT_REV',[(22.0375,15),(20.8,15)],1.2,B),('/BAT_MON',[(27.9625,15),(29.2,15)],1.2,B),('/+5V_MOTION',[(7.95,20.625),(9.2,20.625)],.4,F)]:
 g=Guard(b,net)
 if not g.line_clear(*points,l,w):print('BLOCKED NECK',net,flush=True);continue
 track(b,net,points,w,l)
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'power_corridor_moves.json').write_text(json.dumps(dict(moves=moves,removed=removed),ensure_ascii=False,indent=2)+'\n');print('Power corridor components updated',flush=True)
