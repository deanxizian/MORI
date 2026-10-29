"""Independent four-part swap geometry: move the divider near U1702 and the current filter toward U1001, after releasing exact source terminal traces. Restored circuits and joint placement remain unproven.

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

b=Path('robot/.state/c3-completion/trials');out=b/'R186-four-part-pose-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
for path,name in [(b/'R138_joint_search.py','fab'),(b/'R167_joint_pose_screen.py','outline')]:
 node=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'))
selected=[f for f in c.footprints if f.GetReference() in ['R1702','R1703','R1102','C1102']]
pad_ids={uid(p) for f in selected for p in f.Pads()};tracks=[t for t in c.segments if t.GetLayer()==pcb.F_Cu]
lead_ids=set();terminals={}
for p in [p for f in selected for p in f.Pads()]:
 net=p.GetNetname();own=c.shapes[uid(p),'F.Cu'];todo=[t for t in tracks if t.GetNetname()==net and c.shapes[uid(t),'F.Cu'].intersects(own)];seen=set();stops=set()
 while todo:
  t=todo.pop();u=uid(t)
  if u in seen:continue
  seen.add(u);s=c.shapes[u,'F.Cu'];lead_ids.add(u)
  anchors=[a for a in c.anchors(net) if uid(a) not in pad_ids and (uid(a),'F.Cu') in c.shapes and s.intersects(c.shapes[uid(a),'F.Cu'])]
  if anchors:
   stops.update(c.pad_name(a) for a in anchors);continue
  todo.extend(q for q in tracks if uid(q) not in seen and q.GetNetname()==net and s.intersects(c.shapes[uid(q),'F.Cu']))
 terminals[c.pad_name(p)]=dict(track_uuids=sorted(seen),stops=sorted(stops))
assert lead_ids and len(lead_ids)<40
other_bodies=unary_union([fab(o) for o in c.footprints if o.GetLayer()==pcb.F_Cu and o.GetReference() not in ['R1702','R1703','R1102','C1102']])
other_yards=unary_union([outline(o,pcb.F_CrtYd) for o in c.footprints if o.GetLayer()==pcb.F_Cu and o.GetReference() not in ['R1702','R1703','R1102','C1102']])
fixed_tracks=unary_union([c.shapes[uid(t),'F.Cu'] for t in tracks if uid(t) not in lead_ids])
vias=unary_union([c.shapes[uid(v),'F.Cu'] for v in c.vias if (uid(v),'F.Cu') in c.shapes])
pads=[p for p in c.pads if uid(p) not in pad_ids and (uid(p),'F.Cu') in c.shapes]
nets={p.GetNetname() for f in selected for p in f.Pads()}
foreign={n:unary_union([s for (u,l),s in c.shapes.items() if l=='F.Cu' and u not in pad_ids|lead_ids and c.by_id[u].GetNetname()!=n]) for n in nets}
all_poses={};rejections={};tested=0
for f in selected:
 origin=xy(f.GetPosition());angle=f.GetOrientationDegrees();ref=f.GetReference();owned=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')]
 old_body=unary_union([k['shape'] for k in owned if k['tracks']]);old_via=unary_union([k['shape'] for k in owned if k['vias']]);fixed_cutouts=old_body.difference(old_via) if not old_via.is_empty else GeometryCollection()
 reject=collections.Counter();poses=[]
 for ix in (range(212,253) if ref in ['R1702','R1703'] else range(188,211)):
  for iy in (range(48,105) if ref in ['R1702','R1703'] else range(24,49)):
   x,y=ix*.25,iy*.25;dx,dy=x-origin[0],y-origin[1]
   for new_angle in [0,90,180,270]:
    tested+=1;q=pcb.FOOTPRINT(f);q.SetOrientationDegrees(new_angle);q.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)))
    body=fab(q);yard=outline(q,pcb.F_CrtYd)
    if body.intersection(other_bodies).area>1e-8 or yard.intersection(other_yards).area>1e-8:reject['body_or_courtyard']+=1;continue
    if any(yard.intersection(c.shapes[uid(p),'F.Cu']).area>1e-8 for p in pads):reject['pad_in_courtyard']+=1;continue
    pp={p.GetNumber():p for p in q.Pads()}
    if any(shape(p,pcb.F_Cu).distance(vias)<.2-1e-6 for p in pp.values()):reject['via_pad']+=1;continue
    if any(shape(p,pcb.F_Cu).distance(foreign[p.GetNetname()])<.2-1e-6 for p in pp.values()):reject['pad_or_retained_copper']+=1;continue
    transform=lambda s:translate(rotate(s,-(new_angle-angle),origin=origin),xoff=dx,yoff=dy)
    guards=unary_union([transform(k['shape']) for k in owned if k['tracks'] and 'F.Cu' in k['layers']])
    if guards.intersects(fixed_tracks):reject['native_body_tracks']+=1;continue
    via_guards=transform(old_body).difference(fixed_cutouts) if not old_via.is_empty else GeometryCollection()
    if via_guards.intersects(vias):reject['native_body_vias']+=1;continue
    poses.append(dict(position_mm=[x,y],delta_mm=[dx,dy],rotation_deg=new_angle,pads={n:list(xy(p.GetPosition())) for n,p in pp.items()},input_distance_mm=math.dist(xy(pp['2'].GetPosition()),(58.8,16.3875))))
 poses.sort(key=lambda r:r['input_distance_mm']);all_poses[ref]=poses;rejections[ref]=dict(reject)
 print(ref,'poses',len(poses),'examples',poses[:3],flush=True)
result=dict(scope=__doc__,source_sha256=c.sha,released_terminal_tracks=sorted(lead_ids),terminal_inventory=terminals,tested_poses=tested,rejections=rejections,poses=all_poses,adopted=False,native_DRC='NOT_TESTED',limits='Two independent part screens; mutual collision, complete supply/input routing, native refill and all original checks still required.')
out.write_text(json.dumps(result,indent=2)+'\n')
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
