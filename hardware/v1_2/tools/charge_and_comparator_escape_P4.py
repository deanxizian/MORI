"""Keep the comparator's adjacent pins in parallel outward escape lanes."""
import pcbnew as k,json
from helpers_P4 import paths
from layout_P3R1 import setplace,track,via,xy,F,B
from body_keepouts_P3R1 import create
from geometry_guard_P3R1 import Guard
_,d,p,r=paths('power');b=k.LoadBoard(str(p));k.SaveBoard(str(r/'before_comparator_escape.kicad_pcb'),b)
f=next(f for f in b.GetFootprints() if f.GetReference()=='R56');oldpads=list(f.Pads())
for t in list(b.GetTracks()):
 if t.GetNetname() in ['/H_OVSENSE','/CHG_BASE'] or (t.GetNetname()=='/GND' and t.Type()!=k.PCB_VIA_T and t.IsOnLayer(B) and any(t.GetEffectiveShape(B).Collide(q.GetEffectiveShape(B),0) for q in oldpads)):b.Delete(t)
setplace(f,69.5,36.6,0,'B');create(b);log=[]
for net,y in [('/H_REF',37.095),('/H_OVSENSE',38.365)]:
 ps=[(65.475,y),(67.2,y)]
 ok=Guard(b,net).line_clear(*ps,B,.2) and Guard(b,net).via_clear((67.2,y))
 print(net,'escape',ok)
 if ok:track(b,net,ps,.2,B);via(b,net,67.2,y,grid=False);log.append(dict(net=net,points=ps,via=[67.2,y]))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);(r/'comparator_escapes.json').write_text(json.dumps(log,indent=2)+'\n')
