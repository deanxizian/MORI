"""Independent opposite-face R402 pose comparison after releasing both local signal tails and bus branches.

All other parts, pads, vias, native rules, body avoidance and fixed interfaces
remain. This screen is geometric only; both terminals require full access and
native restoration. Neither a candidate nor a global routability conclusion.
"""
import ast,collections,json,math,sys
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R190-R402-front-pose-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
    node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
f=next(f for f in c.footprints if f.GetReference()=='R402')
origin=xy(f.GetPosition());angle0=f.GetOrientationDegrees();mine={uid(p) for p in f.Pads()}
retired={'38b1aa1f-6d6c-5391-ae66-8dc9df61b001','ad23fc9d-55cc-5e3c-910c-9b49312999af','42236b96-3e31-4ab6-8c05-84597540bf84','62f4fe96-15c4-4c6e-8659-1450215f3dcf','06516b20-ba36-405f-86bc-58bf187b0ee4','364a8831-1edb-4a26-9963-10aa62748be3'}
assert all(u in c.by_id for u in retired)
moving_via='5cc2b6b0-e919-4910-b0af-8902a95393d9'
assert c.by_id[moving_via].GetNetname()=='Net-(U402-1Y)'
retired.add(moving_via)
owned=[k for k in c.keepouts if k['name'].startswith('BODY_R402_')]
guard=unary_union([k['shape'] for k in owned]);assert all(k['tracks'] and k['vias'] for k in owned)
bodies=unary_union([fab(o) for o in c.footprints if o.GetLayer()==pcb.F_Cu and o.GetReference()!='R402'])
yards=unary_union([outline(o,pcb.F_CrtYd) for o in c.footprints if o.GetLayer()==pcb.F_Cu and o.GetReference()!='R402'])
mounts=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'F.Cu' in k['layers']])
pth_lands=unary_union([s for (u,ly),s in c.shapes.items() if ly=='F.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetAttribute()==pcb.PAD_ATTRIB_PTH])
holes=unary_union([Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
vias=unary_union([c.shapes[uid(v),'F.Cu'] for v in c.vias if uid(v) not in retired])
tracks=unary_union([c.shapes[uid(t),'F.Cu'] for t in c.segments if t.GetLayer()==pcb.F_Cu and uid(t) not in retired])
nets={p.GetNetname() for p in f.Pads()}
foreign={n:unary_union([s for (u,ly),s in c.shapes.items() if ly=='F.Cu' and u not in mine|retired and c.by_id[u].GetNetname()!=n]) for n in nets}
targets={n:unary_union([s for (u,ly),s in c.shapes.items() if ly=='F.Cu' and u not in mine|retired and c.by_id[u].GetNetname()==n]) for n in nets}
positions=[(x/4,y/4) for x in range(192,257) for y in range(40,73)]+[origin]
rows=[];reject=collections.Counter()
for angle in [0,90,180,270]:
    part=pcb.FOOTPRINT(f);part.Flip(part.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT);part.SetOrientationDegrees(angle)
    body,yard=fab(part),outline(part,pcb.F_CrtYd)
    gd=rotate(guard,-(angle-angle0),origin=origin)
    pads={p.GetNumber():(p.GetNetname(),shape(p,c.ids['F.Cu']),xy(p.GetPosition())) for p in part.Pads()}
    for pos in positions:
        dx,dy=pos[0]-origin[0],pos[1]-origin[1]
        bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
        if bo.intersection(bodies).area>1e-8 or ya.intersection(yards).area>1e-8 or ya.intersection(mounts).area>1e-8:
            reject['body_courtyard_mount']+=1;continue
        pp={k:(n,translate(s,xoff=dx,yoff=dy),(pt[0]+dx,pt[1]+dy)) for k,(n,s,pt) in pads.items()}
        if not box(.5,.5,69.5,34.5).covers(unary_union([bo]+[s for n,s,pt in pp.values()])):
            reject['board_edge']+=1;continue
        if ya.intersection(pth_lands).area>1e-8:
            reject['PTH_inside_courtyard']+=1;continue
        if bo.intersects(holes) or any(s.distance(holes)<.299999 for n,s,pt in pp.values()):
            reject['native_drill_clearance']+=1;continue
        if any(s.distance(vias)<.1999996-1e-9 or s.distance(foreign[n])<.1999996-1e-9 for n,s,pt in pp.values()):
            reject['pad_clearance']+=1;continue
        gg=translate(gd,xoff=dx,yoff=dy)
        if gg.intersection(vias).area>1e-8 or gg.intersection(tracks).area>1e-8:
            reject['native_body_guard']+=1;continue
        if bo.difference(unary_union([s for n,s,pt in pp.values()])).intersection(tracks).area>1e-8:
            reject['same_face_body_trace']+=1;continue
        gaps={k:s.distance(targets[n]) for k,(n,s,pt) in pp.items()}
        rows.append(dict(position_mm=list(pos),rotation_deg=angle,displacement_mm=math.dist(pos,origin),
            pads={k:dict(net=n,position_mm=list(pt)) for k,(n,s,pt) in pp.items()},target_gaps_mm=gaps))
rows.sort(key=lambda r:(r['target_gaps_mm']['1'],sum(r['target_gaps_mm'].values())))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,retired_tracks=sorted(retired),
    candidate_face='F.Cu',grid_mm=.25,region_mm=[48,10,64,18],
    candidates=rows,rejections=dict(reject),adopted=False),indent=2)+'\n')
print(json.dumps(dict(poses=len(rows),rejections=dict(reject),top=rows[:6])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
