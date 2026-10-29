"""Read-only route search retaining native rules, mounted-face bodies and existing references."""
import ast, json, sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner, mask
b = Path('robot/.state/c3-completion/trials')
label, board, net = sys.argv[1:4]
out = b / (label + '-search')
out.mkdir(exist_ok=False)
p = Planner(board, .05, ['B.Cu','In3.Cu','F.Cu','In2.Cu'], .2)
c = p.c
node = next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
free, vf, blocked, allowed = p.geometry(net)
blocked = list(blocked)
for k, ly in enumerate(p.layers):
    if ly in ['F.Cu','B.Cu']:
        bodies = unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
        own = unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
        blocked[k] = unary_union([blocked[k], bodies.buffer(.102).difference(own.buffer(-.001))])
free = np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
gs = p.routing_groups(net)
rows = []
for i,a in enumerate(gs):
    for j,t in enumerate(gs[i+1:],i+1):
        r = p.solve(a,t,(free,vf,blocked,allowed),700000)
        row = dict(source_sha256=c.sha,net=net,groups=[a['pads'],t['pads']],result=r)
        rows.append(row)
        (out/'search.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps(row),flush=True)
        if r['status']=='PROPOSAL':
            plan=dict(revision=label,board_sha256=c.sha,scope=__doc__,routes=[dict(net=net,**x) for x in r['routes']],vias=[dict(net=net,**x) for x in r['vias']],activate_pth_layers=r.get('activate_pth_layers',[]))
            (out/('plan-'+str(i)+'-'+str(j)+'.json')).write_text(json.dumps(plan,indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
