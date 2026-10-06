"""Rotate R40 to face its shunt reference and remove the long detour."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import setplace,track,xy,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_reference_corridor.kicad_pcb'),b)
f=next(f for f in b.GetFootprints() if f.GetReference()=='R40');pads=list(f.Pads());removed=[]
for t in list(b.GetTracks()):
 if t.GetNetname()=='/H_REF' or (t.GetNetname()=='/H_VM' and any(t.IsOnLayer(B) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),0) for q in pads)) or (t.GetNetname()=='/PACK_FUSED' and t.GetLayer()==F and t.Type()!=k.PCB_VIA_T and k.ToMM(t.GetWidth())>1.9):
  removed.append(t.m_Uuid.AsString());b.Delete(t)
setplace(f,52.5,34,270,'B');create(b)
ps=[(14,7),(14,3.2),(12.8,2),(7.3,2),(7.3,4.4),(1.65,10.05),(1.65,12)]
bad=[(a,z) for a,z in zip(ps,ps[1:]) if not Guard(b,'/PACK_FUSED').line_clear(a,z,F,2)]
if bad:print('PACK corridor blocked',bad)
else:track(b,'/PACK_FUSED',ps,2,F)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'reference_corridor.json').write_text(json.dumps(dict(R40_rotation_deg=270,removed_copper=removed,pack_route_added=not bad),indent=2)+'\n')
