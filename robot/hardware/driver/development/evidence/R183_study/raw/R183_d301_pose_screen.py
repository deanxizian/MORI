"""Read-only D301 relocation screen near the fixed MCU reset header.

Only D301 and its obsolete CLR terminal tail are prospectively released. The
retained CLR spine is restored explicitly. No fixed mount, connector, original
via, other component, native keepout or acceptance threshold is relaxed.
"""
import ast,collections,json,math,sys
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R183-D301-pose-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
    node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
f=next(f for f in c.footprints if f.GetReference()=='D301')
origin=xy(f.GetPosition());angle0=f.GetOrientationDegrees();mine={uid(p) for p in f.Pads()}
retired={'a64ead90-f8fb-47e5-9d8d-700e6f43096f'}
t=c.by_id[next(iter(retired))]
assert (t.GetNetname(),c.board.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()))==('/CLR_N','B.Cu',(32.1,13.15),(32.1,14.95))
replacement=LineString([(32.1,13.15),(32.1,13.85)]).buffer(.1)
owned=[k for k in c.keepouts if k['name'].startswith('BODY_D301_')]
guard=unary_union([k['shape'] for k in owned]);assert all(k['tracks'] and k['vias'] for k in owned)
bodies=unary_union([fab(o) for o in c.footprints if o.GetLayer()==pcb.B_Cu and o.GetReference()!='D301'])
yards=unary_union([outline(o,pcb.B_CrtYd) for o in c.footprints if o.GetLayer()==pcb.B_Cu and o.GetReference()!='D301'])
mounts=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']])
holes=unary_union([Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
vias=unary_union([c.shapes[uid(v),'B.Cu'] for v in c.vias])
tracks=unary_union([c.shapes[uid(t),'B.Cu'] for t in c.segments if t.GetLayer()==pcb.B_Cu and uid(t) not in retired]+[replacement])
nets={p.GetNetname() for p in f.Pads()}
foreign={n:unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in mine|retired and c.by_id[u].GetNetname()!=n]+([] if n=='/CLR_N' else [replacement])) for n in nets}
targets={n:unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in mine|retired and c.by_id[u].GetNetname()==n]+([replacement] if n=='/CLR_N' else [])) for n in nets}
positions=[(x/4,y/4) for x in range(104,165) for y in range(52,125)]+[origin]
rows=[];reject=collections.Counter()
for angle in [0,90,180,270]:
    part=pcb.FOOTPRINT(f);part.SetOrientationDegrees(angle)
    body,yard=fab(part),outline(part,pcb.B_CrtYd)
    gd=rotate(guard,-(angle-angle0),origin=origin)
    pads={p.GetNumber():(p.GetNetname(),shape(p,c.ids['B.Cu']),xy(p.GetPosition())) for p in part.Pads()}
    for pos in positions:
        dx,dy=pos[0]-origin[0],pos[1]-origin[1]
        bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
        if bo.intersection(bodies).area>1e-8 or ya.intersection(yards).area>1e-8 or ya.intersection(mounts).area>1e-8:
            reject['body_courtyard_mount']+=1;continue
        pp={k:(n,translate(s,xoff=dx,yoff=dy),(pt[0]+dx,pt[1]+dy)) for k,(n,s,pt) in pads.items()}
        if not box(.5,.5,69.5,34.5).covers(unary_union([bo]+[s for n,s,pt in pp.values()])):
            reject['board_edge']+=1;continue
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
    replacement_clr_spine_mm=[[32.1,13.15],[32.1,13.85]],grid_mm=.25,region_mm=[26,13,41,31],
    candidates=rows,rejections=dict(reject),adopted=False),indent=2)+'\n')
print(json.dumps(dict(poses=len(rows),rejections=dict(reject),closest_to_reset=rows[:12])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
