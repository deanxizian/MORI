"""Read-only 0.50 mm bridge between actual 0.48 mm connected components.

Start/end at named existing via centres, not arbitrary thin copper of a net that
is already connected at width zero. No new vias. Native physical/reference rules,
mounted-face nominal bodies and foreign power-fill reservations remain.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');rev=sys.argv[1];out=b/(rev+'-width-restore');out.mkdir(exist_ok=False)
p=Planner(str(b/rev/'MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','In2.Cu','F.Cu'],.5);c=p.c;net='MOTION_3V3'
a=json.loads((b/(rev+'-audit.json')).read_text());old=next(x for x in a['power_width'] if x['net']==net and x['width_mm']==.48)
needed={u for pair in old['lost_pairs'] for u in pair};pairs=c.connected_pairs(net,.48);gs=[]
while needed:
 u=min(needed);ids={u}|{v if k==u else k for k,v in pairs if k==u or v==u};ids &= needed;needed-=ids
 terminals=[c.by_id[x] for x in sorted(ids)];assert all(isinstance(x,pcb.PCB_VIA) for x in terminals)
 gs.append({'pads':[],'ids':sorted(ids),'layers':{ly:unary_union([Point(xy(v.GetPosition())).buffer(.04) for v in terminals if (uid(v),ly) in c.shapes]) for ly in p.layers}})
assert len(gs)==2,len(gs)
node=next(x for x in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
free,vf,blocked,allowed=p.geometry(net)
for i,ly in enumerate(p.layers):
 fills=unary_union([s for n,l,s in c.fills if l==ly and n not in ['GND',net]])
 blocked[i]=unary_union([blocked[i],fills.buffer((p.internal_clearance if ly.startswith('In') else .2)+.255)])
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly])
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=unary_union([blocked[i],bodies.buffer(.252).difference(own.buffer(-.001))])
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
r=p.solve(gs[0],gs[1],(free,np.zeros(vf.shape,dtype=bool),blocked,allowed),700000)
snaps=[]
if r['status']=='PROPOSAL':
 for group,route,index in [(gs[0],r['routes'][0],0),(gs[1],r['routes'][-1],-1)]:
  pt=Point(route['points_mm'][index]);near=[c.by_id[u] for u in group['ids'] if Point(xy(c.by_id[u].GetPosition())).distance(pt)<.041]
  assert len(near)==1
  centre=list(xy(near[0].GetPosition()));adj=route['points_mm'][1 if index==0 else -2]
  line=LineString([centre,adj]);i=p.layers.index(route['layer'])
  ok=not line.intersects(blocked[i]) and allowed[i].covers(line)
  snaps.append({'via_uuid':uid(near[0]),'position_mm':centre,'geometry_pass':ok})
  route['points_mm'][index]=centre
 r['centre_snap_status']='PASS' if all(x['geometry_pass'] for x in snaps) else 'FAIL'
 r['length_mm']=sum(LineString(x['points_mm']).length for x in r['routes'])
row={'source_sha256':c.sha,'scope':__doc__,'width_components':[g['ids'] for g in gs],'snaps':snaps,'result':r}
(out/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
