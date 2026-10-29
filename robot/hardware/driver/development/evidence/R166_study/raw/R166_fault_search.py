"""Extend the one current-board FAULT search that exhausted its state budget.

Read-only proposal search with unchanged native/reference/body constraints.
This is a bounded search, not proof of routability or electrical acceptance.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials')
out=b/'R166-fault-extended-search.json';assert not out.exists()
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.05,['F.Cu','B.Cu','In2.Cu','In3.Cu'],.2)
c=p.c;assert c.sha=='899d526fda5da465fe2279448a0d2561bf6d0b5e6e964d478cfda28ddfad4f70'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
net='/FAULT_N';free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
    if ly not in ['F.Cu','B.Cu']:continue
    bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
    lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
    blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
gs=p.routing_groups(net);a=next(g for g in gs if 'J102.7' in g['pads']);z=next(g for g in gs if 'Q1701.3' in g['pads'])
print('Starting extended search, 2000000 states',flush=True)
r=p.solve(a,z,(free,vf,blocked,allowed),2000000)
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,net=net,endpoint_groups=[a['pads'],z['pads']],result=r,adopted=False),indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ['routes','vias','prospective_pth_terminals']}),flush=True)
print('Vias',r.get('vias',[]),flush=True)
