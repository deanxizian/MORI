"""Rotate J1 180 degrees to align positive input with Q90's source bank."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import xy,pt,setplace,track,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_J1_rotation.kicad_pcb'),b)
f=next(f for f in b.GetFootprints() if f.GetReference()=='J1');oldpad=next(q for q in f.Pads() if q.GetNumber()=='1');old=xy(oldpad.GetPosition());changes=[]
for t in list(b.GetTracks()):
 if t.GetNetname()=='/PACK_FUSED' and t.Type()!=k.PCB_VIA_T and t.GetLayer()==F and k.ToMM(t.GetWidth())>1.9:b.Delete(t);continue
 if t.GetNetname()=='/GND' and t.Type()!=k.PCB_VIA_T:
  if xy(t.GetStart())==old:t.SetStart(pt(14,7));changes.append(t.m_Uuid.AsString())
  if xy(t.GetEnd())==old:t.SetEnd(pt(14,7));changes.append(t.m_Uuid.AsString())
setplace(f,14,7,180,'F');create(b)
ps=[(9,7),(6.5,7),(1.65,11.85),(1.65,12)]
bad=[(a,z) for a,z in zip(ps,ps[1:]) if not Guard(b,'/PACK_FUSED').line_clear(a,z,F,2)]
if bad:print('PACK manual blocked',bad)
else:track(b,'/PACK_FUSED',ps,2,F)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'pack_connector_rotation.json').write_text(json.dumps(dict(rotation_deg=180,position_mm=[14,7],pin1_GND_mm=[14,7],pin2_PACK_FUSED_mm=[9,7],changed_ground_starts=changes,wide_path_added=not bad),indent=2)+'\n')
