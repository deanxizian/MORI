"""Bounded B-face VS restoration search on the refilled R171C candidate.

Native keepouts, 0.2 mm width/clearance, own-face bodies and full reference
requirements remain enabled. No new vias or board mutation; not qualification.
"""
import ast,json,sys,time
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials')
out=b/'R171C-supply-search';out.mkdir(exist_ok=False)
p=Planner(str(b/'R171C/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu'],.2)
c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
net='MOTION_3V3';gs=p.routing_groups(net)
a=next(g for g in gs if 'C1701.1' in g['pads'])
z=next(g for g in gs if 'C505.1' in g['pads'])
bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())=='B.Cu'])
lands=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
rows=[]
for grid in [.025,.01]:
 p.grid=grid;p.xs=np.arange(41.,53.501,grid);p.ys=np.arange(8.,15.501,grid);p.xx,p.yy=np.meshgrid(p.xs,p.ys)
 start=time.monotonic();free,vf,blocked,allowed=p.geometry(net)
 blocked[0]=unary_union([blocked[0],bodies.buffer(.102).difference(lands.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 r=p.solve(a,z,(free,np.zeros_like(vf),blocked,allowed),1500000)
 row=dict(grid_mm=grid,result=r,elapsed_seconds=time.monotonic()-start);rows.append(row)
 (out/'searches.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,groups=[a['pads'],z['pads']],bounds_mm=[41,8,53.5,15.5],results=rows,adopted=False),indent=2)+'\n')
 print(json.dumps(row),flush=True)
 if r['status']=='PROPOSAL':break
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
