"""Bounded same-net supply repair proposals on R158C; no new holes or rule changes.

These are not acceptable boards; source shorts, LIMIT/reference failures and
all power-plane regressions still require native joint repair and review.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R158-supply-repair-proposals.json';assert not out.exists();rows=[]
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
for net,layers,width in [('MOTION_3V3',['In2.Cu'],.5),('/06 {slash} CAM_Buck/UPS_5V',['B.Cu','In3.Cu','F.Cu'],.4)]:
 p=Planner(b/'R158C/MORI_Interface_C3.kicad_pcb',.05,layers,width);c=p.c;gs=p.routing_groups(net);assert len(gs)==2
 free,vf,blocked,allowed=p.geometry(net);vf[:]=False
 for k,ly in enumerate(layers):
  if ly not in ['F.Cu','B.Cu']:continue
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]);own=unary_union([g for (u,l),g in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);blocked[k]=unary_union([blocked[k],bodies.buffer(width/2+.002).difference(own.buffer(-.001))])
 free=np.asarray([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)]);r=p.solve(gs[0],gs[1],(free,vf,blocked,allowed),500000)
 rows.append({'net':net,'width_mm':width,'layers':layers,'group_pad_counts':[len(g['pads']) for g in gs],'result':r});out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'rows':rows,'adopted':False},indent=2)+'\n');print(json.dumps({'net':net,**r}),flush=True)
