"""Read-only same-face routes for relocated R301, no new transfers permitted."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-same-face-pullup');out.mkdir(exist_ok=False)
tree=ast.parse((b/'R138_joint_search.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'),globals())
rows=[]
for net,src,dst,width in [('/CLR_N','R301.1','J102.4',.2),('MOTION_3V3','R301.2','C301.1',.5)]:
 p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu'],width);c=p.c
 gs=p.routing_groups(net);a=next(g for g in gs if src in g['pads']);target=next(g for g in gs if dst in g['pads'])
 if a is target:continue
 free,vf,blocked,allowed=p.geometry(net)
 bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu])
 own=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[0]=unary_union([blocked[0],bodies.buffer(width/2+.002).difference(own.buffer(-.001))])
 free=np.array([~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
 r=p.solve(a,target,(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),600000)
 rows.append({'source_sha256':c.sha,'net':net,'groups':[a['pads'],target['pads']],'width_mm':width,'result':r})
 (out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'net':net,**r}),flush=True)
 assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
