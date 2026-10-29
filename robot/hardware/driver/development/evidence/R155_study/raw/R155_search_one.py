"""Bounded read-only native-rule route proposal; never authorizes adoption."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials')
revision,name,net=sys.argv[1:4];layers=sys.argv[4:]
out=b/(name+'.json');assert not out.exists()
p=Planner(b/revision/'MORI_Interface_C3.kicad_pcb',.1,layers,.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
gs=p.routing_groups(net);assert len(gs)==2,(net,[g['pads'] for g in gs])
_,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly not in ['F.Cu','B.Cu']:continue
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
 lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
print(json.dumps({'net':net,'source':revision,'layers':layers,'groups':[g['pads'] for g in gs]}),flush=True)
r=p.solve(gs[0],gs[1],(free,vf,blocked,allowed),600000)
out.write_text(json.dumps({'scope':__doc__,'source_revision':revision,'source_sha256':c.sha,'net':net,'layers':layers,'groups':[g['pads'] for g in gs],'result':r,'adopted':False,'manufacturing_release':False},indent=2)+'\n')
print(json.dumps(r),flush=True)
