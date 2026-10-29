"""Read-only D302 poses using actual native geometry and reachable FAULT space.

Relax only the moving D302 footprint/owned guards; the five explicitly replaced
CLR leads were already removed in R177A. All other components, copper, supply
reservations and reference constraints remain. Reachability is optimistic until
the moved D302's own body and other pin are reintroduced in a native candidate.
No absent raster route is a proof that the board must be enlarged.
"""
import ast, collections, json, math, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely import from_wkb
from shapely.affinity import translate,rotate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask

b=Path('robot/.state/c3-completion/trials');out=b/'R177-D302-pose-access.json';assert not out.exists()
p=Planner(str(b/'R177A/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c
f=next(f for f in c.footprints if f.GetReference()=='D302');original=pcb.FOOTPRINT(f)
origin=xy(f.GetPosition());excluded={uid(q) for q in f.Pads()}
owned=[k for k in c.keepouts if k['name'].startswith('BODY_D302_')]
guard=unary_union([k['shape'] for k in owned if k['tracks']])
# Source geometry is read only; changes below affect only the Python view.
c.__dict__['shapes']={k:s for k,s in c.shapes.items() if k[0] not in excluded}
c.__dict__['keepouts']=[k for k in c.keepouts if k not in owned]
c.pads=[q for q in c.pads if uid(q) not in excluded]
c.footprints=[q for q in c.footprints if q.GetReference()!='D302']
common=[p.reference_guard]
common += [s.buffer(.457) for (u,_),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD)]
common += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
common += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
common += [Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0]
common += [c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]).buffer(.657) for t in c.segments if t.GetNetname()=='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
p.via_common=unary_union(common)
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
net='/FAULT_N';free,vf,blocked,allowed=p.geometry(net);blocked=list(blocked)
rdir=b/'R177-supply-reservations-v3';data=json.loads((rdir/'result.json').read_text())
reserved=collections.defaultdict(list)
for row in data['files']:
 payload=(rdir/row['path']).read_bytes();assert hashlib.sha256(payload).hexdigest()==row['sha256']
 reserved[row['layer']].append(from_wkb(payload))
reserved={ly:unary_union(reserved[ly]) for ly in LAYERS}
for i,ly in enumerate(p.layers):
 if ly in ['F.Cu','B.Cu']:
  bodies=unary_union([fab(o) for o in c.footprints if c.board.GetLayerName(o.GetLayer())==ly])
  own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
  blocked[i]=blocked[i].union(bodies.buffer(.102).difference(own.buffer(-.001)))
 blocked[i]=blocked[i].union(reserved[ly].buffer((p.internal_clearance if ly.startswith('In') else .2)+.102))
via_guard=unary_union([g.buffer((p.internal_clearance if ly.startswith('In') else .2)+.252) for ly,g in reserved.items()])
vf &= ~mask(via_guard,p.xx,p.yy)
free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
labels=[];count=0
for fr in free:
 lab,n=ndimage.label(fr,np.ones((3,3)));lab[lab>0]+=count;labels.append(lab);count+=n
parent=list(range(count+1))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def join(a,z):parent[root(int(a))]=root(int(z))
for i in range(len(p.layers)):
 for j in range(i+1,len(p.layers)):
  vm=vf & free[i] & free[j]
  if REFERENCE[p.layers[i]]!=REFERENCE[p.layers[j]]:vm &= p.ground_near
  for a,z in np.unique(np.column_stack([labels[i][vm],labels[j][vm]]),axis=0):join(a,z)
target=next(g for g in p.routing_groups(net) if 'Q1701.3' in g['pads'])
roots=set()
for i,ly in enumerate(p.layers):
 if ly in target['layers']:
  mm=mask(target['layers'][ly].buffer(-.001),p.xx,p.yy,True)&free[i]
  roots.update(root(int(k)) for k in np.unique(labels[i][mm]))
lookup=np.array([root(i) in roots for i in range(count+1)]);lookup[0]=False
reachable=lookup[labels[0]]&free[0]
env=dict(body=unary_union([fab(o) for o in c.footprints if o.GetLayer()==c.ids['B.Cu']]),
 yard=unary_union([outline(o,pcb.B_CrtYd) for o in c.footprints if o.GetLayer()==c.ids['B.Cu']]),
 vias=unary_union([c.shapes[uid(v),'B.Cu'] for v in c.vias]),
 tracks=unary_union([c.shapes[uid(t),'B.Cu'] for t in c.segments if t.GetLayer()==c.ids['B.Cu']]))
foreign={net:unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and c.by_id[u].GetNetname()!=net]) for net in ['/FAULT_N','/CLR_N']}
rows=[];rejects=collections.Counter();start=time.monotonic()
for angle in [0,90,180,270]:
 part=pcb.FOOTPRINT(original);part.SetOrientationDegrees(angle)
 body=fab(part);yard=outline(part,pcb.B_CrtYd);gg=rotate(guard,-(angle-original.GetOrientationDegrees()),origin=origin)
 pads={q.GetNumber():(q.GetNetname(),shape(q,c.ids['B.Cu']),xy(q.GetPosition())) for q in part.Pads()}
 for xi in range(72,137):
  for yi in range(22,73):
   pos=xi/4,yi/4;dx=pos[0]-origin[0];dy=pos[1]-origin[1]
   bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
   if ya.intersection(env['yard']).area>1e-8 or bo.intersection(env['body']).area>1e-8:rejects['part_envelope']+=1;continue
   actual={pin:(net,translate(s,xoff=dx,yoff=dy),(pp[0]+dx,pp[1]+dy)) for pin,(net,s,pp) in pads.items()}
   gd=translate(gg,xoff=dx,yoff=dy)
   if gd.intersection(env['vias']).area>1e-8:rejects['native_via_guard']+=1;continue
   if any(s.distance(env['vias'])<.1999996-1e-9 or s.distance(foreign[net])<.1999996-1e-9 for net,s,pp in actual.values()):rejects['pad_clearance']+=1;continue
   lands=unary_union([s for n,s,pp in actual.values()])
   if gd.intersection(env['tracks']).area>1e-8 or bo.difference(lands).intersection(env['tracks']).area>1e-8:rejects['retained_tracks']+=1;continue
   # Bound the mask to this pad instead of scanning the entire board each pose.
   land=actual['1'][1];x0,y0,x1,y1=land.bounds
   xs=np.where((p.xs>=x0)&(p.xs<=x1))[0];ys=np.where((p.ys>=y0)&(p.ys<=y1))[0]
   access=int((mask(land.buffer(-.001),p.xx[np.ix_(ys,xs)],p.yy[np.ix_(ys,xs)],True)&reachable[np.ix_(ys,xs)]).sum())
   rows.append(dict(position_mm=pos,rotation_deg=angle,pads={pin:dict(net=n,position_mm=pp) for pin,(n,s,pp) in actual.items()},optimistic_fault_access_cells=access,displacement_mm=math.dist(pos,(25.75,7.5))))
rows.sort(key=lambda r:(r['optimistic_fault_access_cells']==0,r['displacement_mm'],r['rotation_deg']))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,reservation_source_sha256=data['source_sha256'],grid_mm=.25,route_grid_mm=.05,bounds_mm=[18,5.5,34,18],candidates=rows,rejections=dict(rejects),elapsed_seconds=time.monotonic()-start,adopted=False),indent=2)+'\n')
print(json.dumps(dict(candidates=len(rows),with_optimistic_fault_access=sum(r['optimistic_fault_access_cells']>0 for r in rows),best=rows[:12],seconds=time.monotonic()-start)),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
