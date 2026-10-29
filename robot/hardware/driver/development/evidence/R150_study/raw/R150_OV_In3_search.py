"""Replan the complete OV branch on In3 while reserving the diagnosed filter corridor.

The old crossing is blocked explicitly. Native copper, holes, keepouts and the
actual ground reference stay hard constraints; no signal obstacle is softened.
"""
import json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R150-OV-In3-search';out.mkdir(exist_ok=False)
p=Planner(b/'R150B/MORI_Interface_C3.kicad_pcb',.05,['In3.Cu'],.2);c=p.c
net='Net-(U1301-INB-_{slash}_OV)';gs=p.routing_groups(net)
source=next(g for g in gs if 'R1306.1' in g['pads']);target=next(g for g in gs if 'R1307.2' in g['pads'])
free,vf,blocked,allowed=p.geometry(net)
d=json.loads((b/'R149-soft-obstacle-diagnostic/diagnosis.json').read_text())[0]
corridor=unary_union([LineString(r['points_mm']).buffer(.405) for r in d['routes'] if r['layer']=='In3.Cu'])
blocked=[blocked[0].union(corridor)]
free=np.array([~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
print(json.dumps(dict(phase='search',groups=[source['pads'],target['pads']])),flush=True)
r=p.solve(source,target,(free,vf,blocked,allowed),500000)
result=dict(scope=__doc__,source_sha256=c.sha,net=net,groups=[source['pads'],target['pads']],result=r)
(out/'search.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(r),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
