"""Propose a real C1403 ground bridge before restoring U303 CLR.

Read only; full mounted-face nominal Fab bodies and native rule areas retained.
Use existing GND vias only, no new transfer or physical qualification.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
base=Path('robot/.state/c3-completion/trials');rev=sys.argv[1]
out=base/(rev+'-ground-before-clr');out.mkdir(exist_ok=False)
tree=ast.parse((base/'R138_joint_search.py').read_text())
node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'),globals())
p=Planner(str(base/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu'],.3);c=p.c
free,vf,blocked,allowed=p.geometry('GND')
bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu])
own=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()=='GND'])
blocked[0]=unary_union([blocked[0],bodies.buffer(.152).difference(own.buffer(-.001))])
free=np.array([~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)])
pad=next(x for x in c.pads if c.pad_name(x)=='C1403.2')
a={'pads':['C1403.2'],'layers':{'B.Cu':c.shapes[(uid(pad),'B.Cu')]}}
rows=[]
for u in ['f52d2645-fd4c-4e4a-948e-9a404f318bd7','de917f62-cfe3-45a6-a8cd-46dafe93ea15']:
 v=c.by_id[u];target={'pads':[],'layers':{'B.Cu':Point(xy(v.GetPosition())).buffer(.035)}}
 r=p.solve(a,target,(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),500000)
 row={'source_sha256':c.sha,'target_via_uuid':u,'target_position_mm':xy(v.GetPosition()),'result':r}
 rows.append(row);(out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n')
 print(json.dumps(row),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
