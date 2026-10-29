"""Independent OV monitor-input proposal, retaining nominal outer-face body avoidance.

This is a low-current monitor input branch, not the actuator current trunk.
All native refill, supply-plane and reference regressions remain mandatory.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R155-OV-route-search.json';assert not out.exists()
p=Planner('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb',.1,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2);c=p.c
assert c.sha=='65ab9844163d4c7e081471e7a877000ebdfe5d17125324ddd78c0050e63ceede'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
net='Net-(U1301-INB-_{slash}_OV)';gs=p.routing_groups(net);assert len(gs)==2
_,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly not in ['F.Cu','B.Cu']:continue
 bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
 lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
print(json.dumps({'groups':[g['pads'] for g in gs],'in2_permitted':net in p.in2_nets,'available_via_cells':int(vf.sum())}),flush=True)
r=p.solve(gs[0],gs[1],(free,vf,blocked,allowed),600000)
d={'scope':__doc__,'source_sha256':c.sha,'groups':[g['pads'] for g in gs],'result':r,'adopted':False,'manufacturing_release':False};out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(r),flush=True)
