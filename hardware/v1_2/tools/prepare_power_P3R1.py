"""Rotate the two series power diodes to align their source/load sides.

Changes only the working P3R1 board. Old copper is logged and then removed;
load paths are reconnected explicitly at their preserved current-path widths.
"""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,setplace,bounds,intersects
from body_keepouts_P3R1 import create
name,d,p,r=paths('power');b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
j=json.loads((r/'drc.json').read_text());bad={i['uuid'] for v in j['violations'] if v['type']=='items_not_allowed' for i in v['items']};removed=[];changes=[]
for ref,pos in [('D10',(49,14,90)),('D30',(25,38,180))]:
 f=fps[ref];old=(*xy(f.GetPosition()),f.GetOrientationDegrees())
 for t in list(b.GetTracks()):
  if isinstance(t,k.PCB_VIA):continue
  if any(t.GetNetCode()==pad.GetNetCode() and t.IsOnLayer(f.GetLayer()) and t.GetEffectiveShape(f.GetLayer()).Collide(pad.GetEffectiveShape(f.GetLayer())) for pad in f.Pads()):bad.add(t.m_Uuid.AsString())
 setplace(f,*pos,'B');box=bounds(f)
 assert not any(q!=f and q.GetLayer()==f.GetLayer() and intersects(box,bounds(q),.12) for q in fps.values()),ref
 changes.append(dict(ref=ref,before=old,after=pos,reason='Input faces supply connector; output faces load switch. Native courtyard comparison required.'))
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString() not in bad and t.GetNetname() not in ['/W9_IN','/H6_IN']:continue
 iv=isinstance(t,k.PCB_VIA);removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),via=iv,layer=b.GetLayerName(t.GetLayer()),start=xy(t.GetStart()),end=xy(t.GetEnd()),width=k.ToMM(t.GetWidth(k.F_Cu) if iv else t.GetWidth())))
 b.Delete(t)
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'power_diode_rotations.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(r/'removed_body_routes.json').write_text(json.dumps(removed,ensure_ascii=False,indent=2)+'\n')
print('Power diode orientation updated; copper removed for explicit repair',len(removed))
