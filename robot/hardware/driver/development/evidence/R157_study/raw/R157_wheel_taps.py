"""Read-only current-source proposals for the two disconnected WHEEL_VM sense taps.

Native R13, hole/pad clearance, body escape and old/new reference guards remain.
The 0.20 mm proposal serves only the named high-value divider input, not the load
power path. Native fill, power and reference verification remain mandatory.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R157-wheel-tap-proposals.json';assert not out.exists()
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.05,['F.Cu','B.Cu','In3.Cu'],.2);c=p.c;net='/WHEEL_VM'
assert c.sha=='83d86e884816d8d5422775d79624ff3db09793066103cba90c762caa4febc8e7'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
gs=p.routing_groups(net);target=next(g for g in gs if 'R1101.2' in g['pads'])
free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly not in ['F.Cu','B.Cu']:continue
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
 lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)]);rows=[]
for pad in ['R1002.1']:
 start=next(g for g in gs if pad in g['pads']);assert start is not target
 print(json.dumps({'phase':'search','pad':pad}),flush=True)
 r=p.solve(start,target,(free,vf,blocked,allowed),600000)
 rows.append({'pad':pad,'result':r});out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'rows':rows,'adopted':False},indent=2)+'\n');print(json.dumps(r),flush=True)
