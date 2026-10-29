"""All-layer local port screen after the exact R186A retirements.

Does not assume a clear outer face implies a legal hole. Opposite/inner copper,
native keepouts, retained reference copper and direct B return paths screened.
Existing source power fill is not frozen into this planning mask: full native
power/refill checks remain mandatory. No source or candidate PCB is saved.
"""
import ast,json,math,sys
from pathlib import Path
import numpy as np
from shapely import intersects_xy,contains_xy,prepare
from shapely.ops import polygonize
from shapely.geometry import box
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R186-port-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');plan=json.loads((b/'R186A-plan.json').read_text());assert plan['board_sha256']==c.sha
omitted=set(plan['delete_copper'])|{x['uuid'] for key in ['move_ground_vias','reassign_vias'] for x in plan[key]}
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
refs=[]
for t in c.segments:
 ly=c.board.GetLayerName(t.GetLayer())
 if uid(t) not in omitted and ly in REFERENCE:
  refs.append(c.shapes[uid(t),ly].intersection(c.copper['GND',REFERENCE[ly]]))
reference_guard=unary_union(refs).buffer(.655)
xx,yy=np.meshgrid(np.arange(50,57.0001,.025),np.arange(12,16.5001,.025))
rows={}
def paths(a,z):
 dx,dy=z[0]-a[0],z[1]-a[1];m=min(abs(dx),abs(dy));sx=1 if dx>=0 else -1;sy=1 if dy>=0 else -1
 for mid in [(a[0]+sx*m,a[1]+sy*m),(z[0]-sx*m,z[1]-sy*m)]:
  pts=[a]
  if math.dist(a,mid)>1e-8 and math.dist(mid,z)>1e-8:pts.append(mid)
  pts.append(z);yield pts
for name,padname in [('C1002_ground','C1002.2'),('WHEEL_sense','C1002.1'),('UPS_SDA','U601.3'),('UPS_SCL','U601.2')]:
 pad=next(p for p in c.pads if c.pad_name(p)==padname);net=pad.GetNetname();pos=xy(pad.GetPosition())
 via_obstacles=[s.buffer(.455) for (u,ly),s in c.shapes.items() if u not in omitted and (isinstance(c.by_id[u],pcb.PAD) or c.by_id[u].GetNetname()!=net)]
 via_obstacles += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.305) for v in c.vias if uid(v) not in omitted]
 via_obstacles += [Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2+.555) for p in c.pads if max(xy(p.GetDrillSize()))>0]
 via_obstacles += [k['shape'].buffer(.255) for k in c.keepouts if k['vias']]
 if net!='GND':via_obstacles.append(reference_guard)
 vg=unary_union(via_obstacles);prepare(vg);legal=~intersects_xy(vg,xx,yy)
 if net=='GND':
  for fill in c.reference_ground_fills.values():
   prepare(fill);legal &= contains_xy(fill,xx,yy)
 ys,xs=np.where(legal);positions=sorted([(float(xx[y,x]),float(yy[y,x])) for y,x in zip(ys,xs)],key=lambda q:math.dist(pos,q))
 ob=[s.buffer(.305) for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in omitted and c.by_id[u].GetNetname()!=net]
 ob += [k['shape'].buffer(.105) for k in c.keepouts if k['tracks'] and 'B.Cu' in k['layers']]
 ob += [fab(f).buffer(.102).difference(c.shapes[uid(pad),'B.Cu'].buffer(-.001)) for f in c.footprints if f.GetLayer()==pcb.B_Cu]
 obstacles=prep(unary_union(ob));routes=[]
 for q in positions:
  if math.dist(pos,q)>4.043503:continue
  options=[]
  for pts in paths(pos,q):
   line=LineString(pts)
   if obstacles.intersects(line):continue
   if net=='GND' and line.length>4.043503:continue
   options.append((line.length,pts))
  if options:
   length,pts=min(options);routes.append(dict(position_mm=[round(t,6) for t in q],B_route_mm=[[round(t,6) for t in p] for p in pts],length_mm=length))
 rows[name]=dict(net=net,pad=padname,all_layer_port_count=len(positions),direct_B_route_count=len(routes),routes=routes)
 print(name,'all-layer holes',len(positions),'direct B exits',len(routes),routes[:2],flush=True)
result=dict(scope=__doc__,source_sha256=c.sha,omitted_exact_uuids=sorted(omitted),window_mm=[50,12,57,16.5],grid_mm=.025,rows=rows,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
