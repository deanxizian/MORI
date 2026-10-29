"""Bounded restoration search using existing native power anchors; no PCB write."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-power-search.json');assert not out.exists()
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
rows=[]
for net,w,ends in [('/01 {slash} Core/MOTION_5V',.4,[[44.5,6.4],[43.55,17.4]]),('/UPS_BAT',.3,[[39.15,13],[45.35,10.5]])]:
 p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','F.Cu'],w);c=p.c
 free,vf,blocked,allowed=p.geometry(net)
 for i,ly in enumerate(p.layers):
  if ly in ['F.Cu','B.Cu']:
   bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
   own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   blocked[i]=unary_union([blocked[i],bodies.buffer(w/2+.002).difference(own.buffer(-.001))])
  allowed[i]=allowed[i].intersection(box(37,4.5,49,20))
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 # Existing vias are explicit targets, not speculative new contacts.
 terminal=[]
 for point in ends:
  v=next(v for v in c.vias if v.GetNetname()==net and Point(xy(v.GetPosition())).distance(Point(point))<1e-7)
  terminal.append({'pads':[uid(v)],'layers':{ly:Point(point).buffer(.10) for ly in p.layers if (uid(v),ly) in c.shapes}})
 r=p.solve(*terminal,(free,vf,blocked,allowed),350000)
 row={'net':net,'width_mm':w,'ends_mm':ends,'source_sha256':c.sha,'result':r,'scope':__doc__};rows.append(row)
 out.write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
 assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
