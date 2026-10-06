"""Short local ground escapes; preserve the real pin and package outlines."""
import json
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from geometry_guard_P5 import Guard
name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b);k.SaveBoard(str(r/'before_last_ground_ports.kicad_pcb'),b)
routes=[[(23.65,25.05),(23.45,24.85),(23.45,24)],[(62.825,21.3),(63.45,21.3),(63.45,19.8)]];vs=[(23.45,24),(63.45,19.8)];new=[]
for ps in routes:new+=track(b,'/GND',ps,.2,F)
for v in vs:
 via(b,'/GND',*v,vd=.6,dr=.3,grid=False);new.append(next(t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and xy(t.GetPosition())==v))
ripped=[]
for t in list(b.GetTracks()):
 if t.GetNetname()=='/GND':continue
 if any(q.IsOnLayer(l)and t.IsOnLayer(l)and q.GetEffectiveShape(l).Collide(t.GetEffectiveShape(l),mm(.205))for q in new for l in[F,B]):
  assert t.GetNetname()=='/W_SENSE',(t.GetNetname(),t.m_Uuid.AsString());ripped.append(t.m_Uuid.AsString());b.Delete(t)
g=Guard(b,'/GND')
for ps in routes:assert all(g.line_clear(a,z,F,.2)for a,z in zip(ps,ps[1:])),ps
for v in vs:assert all(g.clear(v,l,.6,True)for l in[F,B]),v
k.SaveBoard(str(p),b);(r/'last_ground_ports.json').write_text(json.dumps(dict(routes=routes,vias=vs,via_geometry=[.6,.3],displaced_W_SENSE=ripped),indent=2)+'\n')
