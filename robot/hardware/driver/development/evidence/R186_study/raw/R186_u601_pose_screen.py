"""Finite U601 placement comparison after explicitly releasing its terminal tracks.

No board is saved. All native rule areas, retained tracks, fixed interfaces and
via/pad clearances remain; source terminal tracks require complete restoration.
"""
import ast, collections, json, math, sys
from pathlib import Path
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *

b=Path('robot/.state/c3-completion/trials');out=b/'R186-U601-pose-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
for path,name in [(b/'R138_joint_search.py','fab'),(b/'R167_joint_pose_screen.py','outline')]:
 node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'))
f=next(f for f in c.footprints if f.GetReference()=='U601');origin=xy(f.GetPosition());angle=f.GetOrientationDegrees()
pad_ids={uid(p) for p in f.Pads()};tracks=[t for t in c.segments if t.GetLayer()==pcb.B_Cu]
lead_ids=set();terminals={}
for p in f.Pads():
 net=p.GetNetname();own=c.shapes[uid(p),'B.Cu'];todo=[t for t in tracks if t.GetNetname()==net and c.shapes[uid(t),'B.Cu'].intersects(own)];seen=set();stops=set()
 while todo:
  t=todo.pop();u=uid(t)
  if u in seen:continue
  seen.add(u);s=c.shapes[u,'B.Cu'];lead_ids.add(u)
  anchors=[a for a in c.anchors(net) if uid(a) not in pad_ids and (uid(a),'B.Cu') in c.shapes and s.intersects(c.shapes[uid(a),'B.Cu'])]
  if anchors:
   stops.update(c.pad_name(a) for a in anchors);continue
  todo.extend(q for q in tracks if uid(q) not in seen and q.GetNetname()==net and s.intersects(c.shapes[uid(q),'B.Cu']))
 terminals[c.pad_name(p)]=dict(track_uuids=sorted(seen),stops=sorted(stops))
assert lead_ids and len(lead_ids)<40
owned=[k for k in c.keepouts if k['name'].startswith('BODY_U601_')]
old_body=unary_union([k['shape'] for k in owned if k['tracks']]);old_via=unary_union([k['shape'] for k in owned if k['vias']]);fixed_cutouts=old_body.difference(old_via) if not old_via.is_empty else GeometryCollection()
other_bodies=unary_union([fab(o) for o in c.footprints if o.GetLayer()==pcb.B_Cu and o!=f and o.GetReference()!='U601'])
other_yards=unary_union([outline(o,pcb.B_CrtYd) for o in c.footprints if o.GetLayer()==pcb.B_Cu and o.GetReference()!='U601'])
fixed_tracks=unary_union([c.shapes[uid(t),'B.Cu'] for t in tracks if uid(t) not in lead_ids])
vias=unary_union([c.shapes[uid(v),'B.Cu'] for v in c.vias if (uid(v),'B.Cu') in c.shapes])
pads=[p for p in c.pads if uid(p) not in pad_ids and (uid(p),'B.Cu') in c.shapes]
nets={p.GetNetname() for p in f.Pads()}
foreign={n:unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and u not in pad_ids|lead_ids and c.by_id[u].GetNetname()!=n]) for n in nets}
caps={n:next(p for p in c.pads if c.pad_name(p)==n) for n in ['C601.1','C602.1']}
rejections=collections.Counter();poses=[]
for ix in range(-16,17):
 for iy in range(-16,17):
  dx,dy=ix*.125,iy*.125
  for new_angle in [0,90,180,270]:
   q=pcb.FOOTPRINT(f);q.SetOrientationDegrees(new_angle);q.SetPosition(pcb.VECTOR2I(round((origin[0]+dx)*1e6),round((origin[1]+dy)*1e6)))
   body=fab(q);yard=outline(q,pcb.B_CrtYd)
   if not box(.5,.5,69.5,34.5).covers(yard):rejections['edge']+=1;continue
   if body.intersection(other_bodies).area>1e-8 or yard.intersection(other_yards).area>1e-8:rejections['body_or_courtyard']+=1;continue
   if any(yard.intersection(c.shapes[uid(p),'B.Cu']).area>1e-8 for p in pads):rejections['pad_in_courtyard']+=1;continue
   pp={p.GetNumber():p for p in q.Pads()}
   if any(shape(p,pcb.B_Cu).distance(vias)<.2-1e-6 for p in pp.values()):rejections['via_pad']+=1;continue
   if any(shape(p,pcb.B_Cu).distance(foreign[p.GetNetname()])<.2-1e-6 for p in pp.values()):rejections['pad_or_retained_copper']+=1;continue
   transform=lambda s:translate(rotate(s,-(new_angle-angle),origin=origin),xoff=dx,yoff=dy)
   body_guards=unary_union([transform(k['shape']) for k in owned if k['tracks'] and 'B.Cu' in k['layers']])
   if body_guards.intersects(fixed_tracks):rejections['native_body_tracks']+=1;continue
   via_guards=transform(old_body).difference(fixed_cutouts) if not old_via.is_empty else GeometryCollection()
   if via_guards.intersects(vias):rejections['native_body_vias']+=1;continue
   distances={n:math.dist(xy(pp[pn].GetPosition()),xy(caps[n].GetPosition())) for n,pn in [('C601.1','1'),('C602.1','8')]}
   if any(v>4+1e-9 for v in distances.values()):rejections['decoupler_distance']+=1;continue
   poses.append(dict(position_mm=list(xy(q.GetPosition())),delta_mm=[dx,dy],rotation_deg=new_angle,bypass_distances_mm=distances,pads={n:list(xy(p.GetPosition())) for n,p in pp.items()},movement_mm=math.hypot(dx,dy)))
poses.sort(key=lambda r:(r['movement_mm'],r['rotation_deg']))
result=dict(scope=__doc__,source_sha256=c.sha,source_pose=dict(position_mm=origin,rotation_deg=angle),released_terminal_tracks=sorted(lead_ids),terminal_inventory=terminals,
            tested_poses=33*33*4,rejections=dict(rejections),pose_count=len(poses),poses=poses,adopted=False,native_DRC='NOT_TESTED')
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['poses','terminal_inventory','scope']}|{'examples':poses[:8]}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
