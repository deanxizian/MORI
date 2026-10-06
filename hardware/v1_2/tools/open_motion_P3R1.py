"""Create actual space for motion-board outward escapes by moving parts.

J3/J7 move 0.75 mm inward together. Pins and mating orientation stay unchanged.
R2/R9 face their buffer pins directly. This is working CAD, checked afterward.
"""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,setplace,bounds,intersects,F,B
from geometry_guard_P3R1 import Guard
from body_keepouts_P3R1 import create
name,d,p,r=paths('motion');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};moves=[];removed=[]
for ref,pos in [('J3',(59.5,22.25,90)),('J7',(57,30.25,0)),('R2',(21.25,19.75,90)),('R9',(42,12.25,0)),('R19',(40.5,20.5,90)),('R17',(17,17.5,90)),('R6',(41.5,25,270))]:
 f=fps[ref];old=(*xy(f.GetPosition()),f.GetOrientationDegrees());side='B' if f.IsFlipped() else 'F'
 for t in list(b.GetTracks()):
  if isinstance(t,k.PCB_VIA):continue
  if any(t.GetNetCode()==pad.GetNetCode() and t.IsOnLayer(f.GetLayer()) and t.GetEffectiveShape(f.GetLayer()).Collide(pad.GetEffectiveShape(f.GetLayer()),mm(.001)) for pad in f.Pads()):
   removed.append(t.m_Uuid.AsString());b.Delete(t)
 setplace(f,*pos,side)
 box=bounds(f)
 assert not any(q!=f and q.GetLayer()==f.GetLayer() and intersects(box,bounds(q),.12) for q in fps.values()),(ref,box)
 moves.append(dict(reference=ref,before=old,after=pos))
 # Remove old copper that would collide with the relocated physical pads.
 for t in list(b.GetTracks()):
  if any(t.IsOnLayer(f.GetLayer()) and (isinstance(t,k.PCB_VIA) or t.GetNetCode()!=pad.GetNetCode()) and t.GetEffectiveShape(f.GetLayer()).Collide(pad.GetEffectiveShape(f.GetLayer()),mm(.205)) for pad in f.Pads()):
   removed.append(t.m_Uuid.AsString());b.Delete(t)
create(b)
# Buffer-to-series-resistor routes now share a straight axis.
for net,points in [('/HEAD_TX_BUF',[(21.25,22.95),(21.25,20.575)]),('/CAM_RX_BUF',[(38.55,12.25),(41.175,12.25)])]:
 for t in list(b.GetTracks()):
  if t.GetNetname()==net:b.Delete(t)
 # Clear only old signal copper obstructing this deliberate short escape.
 for t in list(b.GetTracks()):
  if not t.IsOnLayer(B) or t.GetNetname()==net:continue
  if any(t.GetEffectiveShape(B).Collide(pt(a[0]+(z[0]-a[0])*i/100,a[1]+(z[1]-a[1])*i/100),mm(.305)) for a,z in zip(points,points[1:]) for i in range(101)):
   removed.append(t.m_Uuid.AsString());b.Delete(t)
 assert Guard(b,net).line_clear(points[0],points[1],B),(net,points)
 track(b,net,points,.2,B)
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'corridor_placement_changes.json').write_text(json.dumps(dict(moves=moves,removed_old_copper=removed),ensure_ascii=False,indent=2)+'\n')
print('Motion corridor placements updated',len(moves),len(removed),flush=True)
