"""Bounded read-only pair search with real native body and reference geometry."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials')
board,label,net,seed1,seed2=sys.argv[1:]
out=b/(label+'-route-search.json');assert not out.exists()
p=Planner(board,.05,['F.Cu','B.Cu'],.2);c=p.c
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
bodies={}
for ly in ['F.Cu','B.Cu']:
 ss=[]
 for f in c.footprints:
  if c.board.GetLayerName(f.GetLayer())!=ly:continue
  g=fab(f)
  if f.GetReference() in ['L701','L901']:
   x,y=xy(f.GetPosition());g=translate(rotate(box(-4.6,-4.25,4.6,4.25),-f.GetOrientationDegrees(),origin=(0,0)),xoff=x,yoff=y)
  ss.append(g)
 bodies[ly]=unary_union(ss)
gs=p.routing_groups(net);a=next(g for g in gs if seed1 in g['pads']);z=next(g for g in gs if seed2 in g['pads'])
print(json.dumps({'net':net,'groups':[a['pads'],z['pads']]}),flush=True)
if a is z:r={'status':'ALREADY_CONNECTED'}
else:
 _,vf,blocked,allowed=p.geometry(net)
 for i,ly in enumerate(p.layers):
  if ly in bodies:
   own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   blocked[i]=unary_union([blocked[i],bodies[ly].buffer(.102).difference(own.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 r=p.solve(a,z,(free,vf,blocked,allowed),500000)
row={'scope':__doc__,'source_sha256':c.sha,'net':net,'groups':[a['pads'],z['pads']],'result':r}
out.write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(r),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
