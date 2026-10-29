"""Read-only joint OV/supply restoration search on a partial, unadopted board."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R155-joint-route-search.json';assert not out.exists()
p=Planner(b/'R155A/MORI_Interface_C3.kicad_pcb',.1,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
results=[]
for net in ['Net-(U1301-INB-_{slash}_OV)','MOTION_3V3']:
 gs=p.routing_groups(net);assert len(gs)==2,(net,[g['pads'] for g in gs])
 _,vf,blocked,allowed=p.geometry(net)
 for i,ly in enumerate(p.layers):
  if ly not in ['F.Cu','B.Cu']:continue
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
  lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(lands.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 print(json.dumps({'net':net,'groups':[g['pads'] for g in gs],'in2_permitted':net in p.in2_nets}),flush=True)
 r=p.solve(gs[0],gs[1],(free,vf,blocked,allowed),600000)
 results.append({'net':net,'groups':[g['pads'] for g in gs],'result':r})
 out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'searches':results,'adopted':False,'manufacturing_release':False},indent=2)+'\n')
 print(json.dumps({'net':net,**r}),flush=True)
