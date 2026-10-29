"""Correct B's native Q1701 body conflict and C1702 reference gap.

Use the explicitly screened ACT x58.775 and capacitor bend x59.925.
Replace the old collinear ACT branch as one segment to keep a native T.
FAULT remains a local unfinished port; this is not an adopted board.
"""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R168C-plan.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
p=json.loads((b/'R168B-plan.json').read_text());assert p['board_sha256']==c.sha
screen=json.loads((b/'R168-local-preflight.json').read_text())
row=next(r for r in screen['rows'] if r['x']==58.775 and r['cap_bend']==59.925);assert not row['hits']
for index,r in zip([2,3,4,7],row['routes']):p['routes'][index].update(points_mm=r['points'],width_mm=r['width'])
u='e74089bf-9fdc-479f-8221-04010d76df9e';t=c.by_id[u]
assert t.GetNetname()=='/17 {slash} Actuator_Overcurrent/ACT_UV_N'
assert xy(t.GetStart())==(58.925,14.775) and xy(t.GetEnd())==(60.275,14.775)
p['delete_copper'].append(u)
p['deleted_copper_expected'][u]=dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
p.update(revision='R168C',scope=__doc__,local_preflight='R168-local-preflight.json',adoption_prohibited=True)
out.write_text(json.dumps(p,indent=2)+'\n');print(out)
