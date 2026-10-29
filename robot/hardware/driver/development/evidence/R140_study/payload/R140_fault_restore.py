"""Read-only search between the exact two displaced FAULT trace ends.

Existing tails stay connected by construction; no dangling copper is silently
deleted. Full mounted-face nominal body and native reference/keepout screening
remain. A finite search is not a routability proof or an acceptance result.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-fault-ends');out.mkdir(exist_ok=False)
p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','F.Cu','In2.Cu'],.2);c=p.c;net='/FAULT_N'
node=next(x for x in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies.buffer(.102).difference(own.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
ends=[[19.15,27.15],[21.4,29.4]]
for pt in ends:assert c.copper[(net,'B.Cu')].covers(Point(pt))
gs=[{'pads':[],'layers':{'B.Cu':Point(pt).buffer(.015)}} for pt in ends]
r=p.solve(gs[0],gs[1],(free,vf,blocked,allowed),800000)
row={'source_sha256':c.sha,'scope':__doc__,'endpoints_mm':ends,'result':r}
(out/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
