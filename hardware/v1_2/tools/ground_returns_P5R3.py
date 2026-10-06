"""Add actual local returns without moving the buck's validated netlist/critical cell.
The wider relocation trial was rejected; this starts from ground_baseline only.
"""
from review_P5R3 import *
from geometry_guard_P5 import Guard
e=Edit('power')
for ref,n,pts,w in [
 ('C61',2,[(22,28.275),(22,29.5)],.5),
 ('C71',2,[(22,42.275),(21.85,42.275),(21.1,43.025)],.3),
 ('C60',2,[(19.5,31.975),(17.5,31.975)],.8),
 ('C70',2,[(18.025,45),(18.025,43)],.8),
 ('C66',2,[(26,32.475),(26,34.125)],.8),
 ('R61',2,[(29.675,31.5),(28.625,31.5)],.2)]:
 g=Guard(e.b,'/GND');print(ref,'guard',g.via_clear(pts[-1]),all(g.line_clear(a,z,F,w)for a,z in zip(pts,pts[1:])),flush=True)
 e.add('/GND',F,pts,w);e.via('/GND',pts[-1])
for t in e.b.GetTracks():
 if isinstance(t,k.PCB_VIA)and xy(t.GetPosition())==(23.45,24):t.SetWidth(mm(.8))
e.check('PWR02_local_returns')
