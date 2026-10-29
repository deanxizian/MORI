"""Independent local restoration proposals on R171D; no PCB mutation.

The GND request uses explicit tracks/pads/vias only as its terminals. All requests
retain original rules, reference guards and mounted-face bodies, and first avoid
all foreign power fills. Failure is bounded; proposals are not jointly validated.
"""
import ast,copy,json,sys,time
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
from plan_existing_copper import groups
b=Path('robot/.state/c3-completion/trials');out=b/'R171D-restore-search';out.mkdir(exist_ok=False)
p=Planner(str(b/'R171D/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','F.Cu','In3.Cu'],.2);c=p.c
p.grid=.025;p.xs=np.arange(39.,54.501,p.grid);p.ys=np.arange(5.,17.501,p.grid);p.xx,p.yy=np.meshgrid(p.xs,p.ys)
ground_anchors=[a for a in c.anchors('GND') if all((uid(a),ref) in c.shapes and c.shapes[uid(a),ref].intersects(p.ground[ref]) for ref in p.ground)]
p.ground_near=mask(unary_union([Point(xy(a.GetPosition())).buffer(1.98) for a in ground_anchors]),p.xx,p.yy,True)
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]) for ly in ['F.Cu','B.Cu']}
native=defaultdict(list)
for (u,ly),g in c.shapes.items():native[c.by_id[u].GetNetname(),ly].append(g)
trace_only=copy.copy(c);trace_only.__dict__['copper']={k:unary_union(v) for k,v in native.items()}
requests=[('enable','MOTION_3V3','U1701.4','C505.1'),('limit','Net-(U1701-LIMIT)','R1701.2','U1701.3'),('in_plus','Net-(U1701-IN+)','R1706.2','U1701.1'),('direct_ground','GND','R1701.1','U1701.8')]
rows=[]
for name,net,aa,zz in requests:
 print(json.dumps(dict(request=name,phase='geometry')),flush=True)
 gs=groups(trace_only,net) if net=='GND' else p.routing_groups(net)
 a=next(g for g in gs if aa in g['pads']);z=next(g for g in gs if zz in g['pads'])
 free,vf,blocked,allowed=p.geometry(net)
 for k,ly in enumerate(p.layers):
  if ly in bodies:
   lands=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   blocked[k]=unary_union([blocked[k],bodies[ly].buffer(.102).difference(lands.buffer(-.001))])
 reserved={ly:unary_union([g for n,l,g in c.fills if l==ly and n not in ['GND',net]]) for ly in LAYERS}
 guards=[reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+.102) for ly in p.layers]
 via_guard=unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in reserved.items()])
 for mode in ['preserve_foreign_fill','native_then_regression']:
  obs=[x.union(y) for x,y in zip(blocked,guards)] if mode=='preserve_foreign_fill' else blocked
  fs=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(obs,allowed)])
  vs=vf & ~mask(via_guard,p.xx,p.yy) if mode=='preserve_foreign_fill' else vf
  start=time.monotonic();r=p.solve(a,z,(fs,vs,obs,allowed),500000)
  row=dict(request=name,net=net,mode=mode,result=r,elapsed_seconds=time.monotonic()-start);rows.append(row)
  (out/'searches.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,grid_mm=p.grid,bounds_mm=[39,5,54.5,17.5],results=rows,adopted=False),indent=2)+'\n')
  print(json.dumps(row),flush=True)
  if r['status']=='PROPOSAL':break
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
