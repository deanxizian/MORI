"""Move the sense-divider resistor out of the brake-current corridor."""
import json
import pcbnew as k
from layout_P3R1 import paths,xy,pt,mm,track,via,setplace,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));f=next(f for f in b.GetFootprints() if f.GetReference()=='R46');before=xy(f.GetPosition())
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA):continue
 if any(t.GetNetCode()==q.GetNetCode() and t.IsOnLayer(B) and t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),mm(.001)) for q in f.Pads()):b.Delete(t)
setplace(f,67,52.5,0,'B');create(b)
# Remove the unused tentative 5V branch from the previous manual pass.
for t in list(b.GetTracks()):
 if not isinstance(t,k.PCB_VIA) and t.GetNetname()=='/+5V_MOTION' and t.GetLayer()==F and (xy(t.GetStart()),xy(t.GetEnd())) in [((17.775,20),(15.5,20)),((15.5,20),(15.5,21.5))]:b.Delete(t)
jobs=[('/+5V_MOTION',[(17.775,20),(14.9,20),(14.9,21.5)],.8,F),('/+5V_MOTION',[(8.1,20.625),(8.975,21.5),(14.9,21.5)],.8,B),('/H_DUMP_D',[(76,45),(76,47),(72.5,50.5),(65,50.5),(65,48)],1,B)]
for net,ps,w,l in jobs:
 assert all(Guard(b,net).line_clear(a,z,l,w) for a,z in zip(ps,ps[1:])),(net,ps)
 track(b,net,ps,w,l)
assert Guard(b,'/+5V_MOTION').via_clear((14.9,21.5),1)
via(b,'/+5V_MOTION',14.9,21.5,vd=1,dr=.45,grid=False)
zones=create(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'body_keepouts.json').write_text(json.dumps(zones,ensure_ascii=False,indent=2)+'\n')
(r/'load_corridor_finish.json').write_text(json.dumps(dict(R46_before_mm=before,R46_after_mm=[67,52.5],wide_routes=jobs),ensure_ascii=False,indent=2)+'\n');print('Load path corridors connected',flush=True)
