"""Read-only dedicated ground-return proposals; general plane fill is not an endpoint path.

Start/target groups contain only native pads, vias and traces. Fills remain in
reference checks but cannot serve as the claimed resistor-to-IC route. No new
holes are allowed in this first comparison. Native body/clearance rules stay.
"""
import ast,json,sys
from pathlib import Path
from collections import defaultdict
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');o=b/'R157-ground-return-proposals.json';assert not o.exists();board=b/'R157B/MORI_Interface_C3.kicad_pcb'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
trace=Copper(board);items=defaultdict(list)
for (u,ly),g in trace.shapes.items():items[trace.by_id[u].GetNetname(),ly].append(g)
trace.__dict__['copper']={k:unary_union(v) for k,v in items.items()};gs=groups(trace,'GND');a=next(g for g in gs if 'R1701.1' in g['pads']);z=next(g for g in gs if 'U1701.8' in g['pads']);assert a is not z;rows=[]
for layers in [['B.Cu'],['F.Cu','B.Cu','In3.Cu']]:
 p=Planner(board,.05,layers,.2);c=p.c;free,vf,blocked,allowed=p.geometry('GND');vf[:]=False
 for k,ly in enumerate(layers):
  if ly not in ['F.Cu','B.Cu']:continue
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]);lands=unary_union([g for (u,l),g in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()=='GND']);blocked[k]=unary_union([blocked[k],bodies.buffer(.102).difference(lands.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)]);print(json.dumps({'phase':'search','layers':layers}),flush=True);r=p.solve(a,z,(free,vf,blocked,allowed),650000);rows.append({'layers':layers,'result':r});o.write_text(json.dumps({'scope':__doc__,'board_sha256':c.sha,'source_pads':a['pads'],'target_pads':z['pads'],'rows':rows,'adopted':False},indent=2)+'\n');print(json.dumps(r),flush=True)
