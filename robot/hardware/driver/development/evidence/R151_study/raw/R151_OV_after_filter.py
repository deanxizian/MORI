"""Rejoin the OV crossing after the real filter route has been built.

Preserve the original OV tail and every existing power pour on internal routing
layers. Compare restoration of the old group and the still-open U1301.4 input.
No source save; all proposals need native refill and full regression afterward.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R151-OV-after-filter';out.mkdir(exist_ok=False)
p=Planner(b/'R151F/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
net='Net-(U1301-INB-_{slash}_OV)';gs=p.routing_groups(net)
a=next(g for g in gs if 'R1306.1' in g['pads']);z=next(g for g in gs if 'R1307.2' in g['pads']);u=next(g for g in gs if 'U1301.4' in g['pads'])
free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)
for k,ly in enumerate(p.layers):
    if ly in ['F.Cu','B.Cu']:
        bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
        own=unary_union([s for (id_,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[id_],pcb.PAD) and c.by_id[id_].GetNetname()==net])
        blocked[k]=blocked[k].union(bodies.buffer(.102).difference(own.buffer(-.001)))
    else:
        foreign=unary_union([s for n,l,s in c.fills if l==ly and n not in ['GND',net]])
        blocked[k]=blocked[k].union(foreign.buffer(p.internal_clearance+.105))
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
rows=[]
for label,source,target in [('restore_old_group',a,z),('source_to_comparator',a,u),('tail_to_comparator',z,u)]:
    print(json.dumps(dict(phase='search',label=label,groups=[source['pads'],target['pads']])),flush=True)
    result=p.solve(source,target,(free,vf,blocked,allowed),500000)
    rows.append(dict(label=label,scope=__doc__,source_sha256=c.sha,net=net,groups=[source['pads'],target['pads']],result=result))
    (out/'search.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(label=label,**result)),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
