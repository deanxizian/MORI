"""Reserve the actual CAM In3 distribution copper while rerouting the complete OV branch.

R151A exposed a starved J702 thermal despite preserved pad connectivity. This
search protects that actual filled region as well as the future filter corridor.
The constraint is stricter than the standard routing proxy; no rule is relaxed.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R151-OV-power-search';out.mkdir(exist_ok=False)
p=Planner(b/'R150B/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
net='Net-(U1301-INB-_{slash}_OV)';gs=p.routing_groups(net)
source=next(g for g in gs if 'R1306.1' in g['pads']);target=next(g for g in gs if 'R1307.2' in g['pads'])
free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)
d=json.loads((b/'R149-soft-obstacle-diagnostic/diagnosis.json').read_text())[0]
for k,ly in enumerate(p.layers):
    if ly in ['F.Cu','B.Cu']:
        bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
        own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
        blocked[k]=blocked[k].union(bodies.buffer(.102).difference(own.buffer(-.001)))
    blocked[k]=blocked[k].union(unary_union([LineString(r['points_mm']).buffer(.405) for r in d['routes'] if r['layer']==ly]))
    if ly=='In3.Cu':
        cam=unary_union([g for n,l,g in c.fills if n=='/07 {slash} CAM_Protection_Start/CAM_BAT_OUT' and l==ly])
        blocked[k]=blocked[k].union(cam.buffer(.405))
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
print(json.dumps(dict(phase='search',groups=[source['pads'],target['pads']])),flush=True)
r=p.solve(source,target,(free,vf,blocked,allowed),500000)
(out/'search.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,net=net,groups=[source['pads'],target['pads']],result=r),indent=2)+'\n');print(json.dumps(r),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
