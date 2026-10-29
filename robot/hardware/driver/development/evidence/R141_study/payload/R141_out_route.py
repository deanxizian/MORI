"""Joint CAM supply / U1401 OUT repair, using the two existing OUT vias.

Compare same-layer paths without new holes. Reserve every existing non-ground
power fill, all native keepouts and the mounted-face Fab bodies (L701/L901 use
documented 9.2 x 8.5 maximum body). Proposals require native full regression.
"""
import ast
import json
import sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner, mask, simplify

b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1]
out=b/(rev+'-OUT-existing-vias');out.mkdir(exist_ok=False)
node=next(x for x in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['F.Cu','B.Cu','In3.Cu'],.2);c=p.c;net='Net-(U1401-OUT)'
vs=[c.by_id[u] for u in ['02b1487e-0eff-44fd-82b0-20ada3d4977f','6c50c7f0-e4bc-4415-93b7-b5a75dd7c9ab']]
assert all(isinstance(v,pcb.PCB_VIA) and v.GetNetname()==net for v in vs)
centres=[list(xy(v.GetPosition())) for v in vs]
free,vf,blocked,allowed=p.geometry(net)
for i,layer in enumerate(p.layers):
 fills=unary_union([s for n,ly,s in c.fills if ly==layer and n not in ['GND',net]])
 blocked[i]=unary_union([blocked[i],fills.buffer((p.internal_clearance if layer.startswith('In') else .2)+.105)])
 if layer not in ['F.Cu','B.Cu']:continue
 bodies=[]
 for f in c.footprints:
  if c.board.GetLayerName(f.GetLayer())!=layer:continue
  body=fab(f)
  if f.GetReference() in ['L701','L901']:
   x,y=xy(f.GetPosition());body=translate(rotate(box(-4.6,-4.25,4.6,4.25),-f.GetOrientationDegrees(),origin=(0,0)),xoff=x,yoff=y)
  bodies.append(body)
 own=unary_union([s for (u,ly),s in c.shapes.items() if ly==layer and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
 blocked[i]=unary_union([blocked[i],unary_union(bodies).buffer(.102).difference(own.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
rows=[]
for i,layer in enumerate(p.layers):
 lf=np.zeros(free.shape,dtype=bool);lf[i]=free[i]
 a,z=[{'pads':[],'layers':{layer:Point(pt).buffer(.038)}} for pt in centres]
 r=p.solve(a,z,(lf,np.zeros(vf.shape,dtype=bool),blocked,allowed),800000)
 if r['status']=='PROPOSAL':
  assert not r['vias'] and len(r['routes'])==1
  route=r['routes'][0];route['points_mm'][0],route['points_mm'][-1]=centres
  route['points_mm']=simplify(route['points_mm']);route['net']=net
  line=LineString(route['points_mm'])
  if line.intersects(blocked[i]) or not allowed[i].covers(line):r['status']='EXACT_CENTRE_SEGMENT_REJECTED'
  r['exact_centerline_length_mm']=line.length
 row={'source_sha256':c.sha,'scope':__doc__,'layer':layer,'result':r}
 rows.append(row);(out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
