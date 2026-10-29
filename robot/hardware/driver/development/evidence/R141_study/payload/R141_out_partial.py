"""Short F-layer bridge for U1401 OUT while reserving a CAM copper passage.

The complete F/B-only paths failed bounded searches. Start at the existing left
OUT via on F and return to In3 through a screened new local via. Retain actual
native keepouts and maximum inductor bodies. The explicitly reserved CAM window
is only a planning constraint; all power and reference regressions remain gates.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask,simplify

b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-OUT-partial');out.mkdir(exist_ok=False)
node=next(x for x in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['F.Cu','In3.Cu'],.2);c=p.c;net='Net-(U1401-OUT)';cam='/07 {slash} CAM_Protection_Start/CAM_BAT_OUT'
free,vf,blocked,allowed=p.geometry(net)
bodies=[]
for f in c.footprints:
 if f.GetLayer()!=pcb.F_Cu:continue
 body=fab(f)
 if f.GetReference() in ['L701','L901']:
  x,y=xy(f.GetPosition());body=translate(rotate(box(-4.6,-4.25,4.6,4.25),-f.GetOrientationDegrees(),origin=(0,0)),xoff=x,yoff=y)
 bodies.append(body)
own=unary_union([s for (u,l),s in c.shapes.items() if l=='F.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
blocked[0]=unary_union([blocked[0],unary_union(bodies).buffer(.102).difference(own.buffer(-.001))])
window=box(17.85,16.15,18.4,18.45)
reserved=c.copper[cam,'In3.Cu'].intersection(window)
blocked[1]=unary_union([blocked[1],reserved.buffer(p.internal_clearance+.105)])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
local=box(18.9,15.8,21.1,17.25)
vf=vf&mask(local,p.xx,p.yy,True)&~mask(reserved.buffer(p.internal_clearance+.257),p.xx,p.yy)
centres=[[17.175,16.925],[27.825,15.575]]
aa={'pads':[],'layers':{'F.Cu':Point(centres[0]).buffer(.038)}}
zz={'pads':[],'layers':{'In3.Cu':Point(centres[1]).buffer(.038)}}
r=p.solve(aa,zz,(free,vf,blocked,allowed),800000)
if r['status']=='PROPOSAL':
 for route,index,pt in [(r['routes'][0],0,centres[0]),(r['routes'][-1],-1,centres[1])]:
  route['points_mm'][index]=pt
 for route in r['routes']:
  route['net']=net;route['points_mm']=simplify(route['points_mm']);i=p.layers.index(route['layer']);line=LineString(route['points_mm'])
  if line.intersects(blocked[i]) or not allowed[i].covers(line):r['status']='EXACT_CENTRE_SEGMENT_REJECTED'
 for via in r['vias']:via['net']=net
 r['exact_length_mm']=sum(LineString(x['points_mm']).length for x in r['routes'])
report={'scope':__doc__,'source_sha256':c.sha,'reserved_CAM_bounds_mm':list(window.bounds),'reserved_CAM_actual_area_mm2':reserved.area,'new_via_search_bounds_mm':list(local.bounds),'eligible_via_cells':int(vf.sum()),'result':r}
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
