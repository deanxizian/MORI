"""Build the newly found FAULT connection from R165M, without placement changes.

Snap the source transfer and Q1701 drain to real native centres after exact
clearance/reference/body preflight. Native fill and power checks remain pending.
"""
import ast,json,sys,copy
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials');out=b/'R166A-plan.json';assert not out.exists()
d=json.loads((b/'R166-fault-extended-search.json').read_text());r=d['result'];assert r['status']=='PROPOSAL'
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.05,['In2.Cu','B.Cu'],.2);c=p.c;assert c.sha==d['source_sha256']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
net=d['net'];_,_,blocked,allowed=p.geometry(net)
own=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu])
blocked[1]=blocked[1].union(bodies.buffer(.102).difference(own.buffer(-.001)))
routes=copy.deepcopy(r['routes']);assert routes[0]['points_mm'][0]==[67.35,28.15]
routes[0]['points_mm'][0]=[67.45,28.35];routes[0]['points_mm'][1]=[65.6,26.5]
target=next(a for a in c.pads if c.pad_name(a)=='Q1701.3');assert target.GetNetname()==net
routes[-1]['points_mm'][-1]=list(xy(target.GetPosition()))
checks=[]
for rt in routes:
    i=p.layers.index(rt['layer'])
    for a,z in zip(rt['points_mm'],rt['points_mm'][1:]):
        line=LineString([a,z]);checks.append(dict(layer=rt['layer'],start=a,end=z,obstacle_hit=bool(line.intersects(blocked[i])),reference_allowed=bool(allowed[i].covers(line))))
(b/'R166A-route-preflight.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,checks=checks),indent=2)+'\n')
assert all(not x['obstacle_hit'] and x['reference_allowed'] for x in checks), 'Exact-centre route preflight failed'
plan=dict(revision='R166A',scope=__doc__,board_sha256=c.sha,routes=[dict(net=net,**x) for x in routes],vias=[dict(net=net,**x) for x in r['vias']],activate_pth_layers=r['activate_pth_layers'])
out.write_text(json.dumps(plan,indent=2)+'\n');print(out)
