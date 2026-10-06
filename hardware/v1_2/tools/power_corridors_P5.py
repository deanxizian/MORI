"""Refine new P5 placement for the major load corridor and Kelvin sensing."""
from layout_P5 import *
from body_P5 import create
from geometry_guard_P5 import Guard
n,d,p,r=paths('power');b=k.LoadBoard(str(p));fs={f.GetReference():f for f in b.GetFootprints()}
(r/'before_power_corridors.kicad_pcb').write_bytes(p.read_bytes())
rip={'/W9_IN','/KELVIN_P','/KELVIN_N','/CURRENT_ADC'}
oldpads=list(fs['U1'].Pads())
for t in list(b.GetTracks()):
 if t.GetNetname() in rip or (t.GetNetname() in ['/GND','/+3V3'] and any(q.GetNetname()==t.GetNetname() and t.GetEffectiveShape(F).Collide(q.GetEffectiveShape(F),0) for q in oldpads)):
  b.Delete(t)
setplace(fs['J3'],35,5.2,0,'F');setplace(fs['U1'],34,18.5,180,'F');create(b,'power')
log=[]
def add(net,ps,w):
 g=Guard(b,net);cc=[g.line_clear(a,z,F,w) for a,z in zip(ps,ps[1:])];print(net,cc,flush=True)
 if all(cc):track(b,net,ps,w,F);log.append(dict(net=net,width=w,points=ps))
add('/W9_IN',[(40,5.2),(43.8,5.2),(44.3,5.7),(44.3,8.15),(43.8,8.65),(40,8.65),(39.5,9.15),(39.5,12.5),(40,13),(40.6,13)],1.5)
add('/KELVIN_P',[(30.825,16.5),(31.3625,16.5),(31.8625,17),(31.8625,18.95),(32.3625,19.45),(32.8625,19.45)],.381)
add('/KELVIN_N',[(38,17.325),(38,18.95),(37.5,19.45),(35.1375,19.45)],.381)
k.SaveBoard(str(p),b);update('power',b);(r/'power_corridors.json').write_text(json.dumps(dict(placement_changes=[dict(ref='J3',dy=-.8,reason='Provide a physical 1.5 mm route above D10'),dict(ref='U1',rotation_deg=180,reason='Align both Kelvin inputs with their filter resistor; remove the crossed sense pair')],routes=log),indent=2)+'\n')
