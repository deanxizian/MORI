"""Native two-face D301 pose comparison including PTH courtyard exclusions.

No PCB edit. Only the original diode and the explicitly trimmed CLR tail are
prospectively released. Mirrored pads preserve pin numbers/net identity.
Native trials, both connections, manufacturer/assembly review remain required.
"""
import ast,collections,json,math,sys
from pathlib import Path
from shapely.affinity import rotate,scale,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R183-D301-two-face-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
    node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
original=next(f for f in c.footprints if f.GetReference()=='D301');origin=xy(original.GetPosition())
mine={uid(p) for p in original.Pads()};retired={'a64ead90-f8fb-47e5-9d8d-700e6f43096f'}
replacement=LineString([(32.1,13.15),(32.1,13.85)]).buffer(.1)
base_guard=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_D301_')])
holes=unary_union([Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
positions=[(x/2,y/2) for x in range(3,138) for y in range(3,68)]+[origin]
rows=[];reject=collections.Counter()
for face in ['B.Cu','F.Cu']:
    f=pcb.FOOTPRINT(original)
    if face=='F.Cu':f.Flip(f.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT)
    assert f.GetLayer()==c.ids[face]
    guard=scale(base_guard,xfact=-1,yfact=1,origin=origin) if face=='F.Cu' else base_guard
    angle0=f.GetOrientationDegrees();nets={p.GetNetname() for p in f.Pads()}
    assert {p.GetNumber():p.GetNetname() for p in f.Pads()}=={p.GetNumber():p.GetNetname() for p in original.Pads()}
    bodies=unary_union([fab(o) for o in c.footprints if o.GetLayer()==c.ids[face] and o.GetReference()!='D301'])
    yard_layer=pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd
    yards=unary_union([outline(o,yard_layer) for o in c.footprints if o.GetLayer()==c.ids[face] and o.GetReference()!='D301'])
    mounts=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and face in k['layers']])
    pth_lands=unary_union([s for (u,ly),s in c.shapes.items() if ly==face and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetAttribute()==pcb.PAD_ATTRIB_PTH])
    vias=unary_union([s for (u,ly),s in c.shapes.items() if ly==face and isinstance(c.by_id[u],pcb.PCB_VIA)])
    tracks=unary_union([s for (u,ly),s in c.shapes.items() if ly==face and isinstance(c.by_id[u],pcb.PCB_TRACK) and not isinstance(c.by_id[u],pcb.PCB_VIA) and u not in retired]+([replacement] if face=='B.Cu' else []))
    foreign={n:unary_union([s for (u,ly),s in c.shapes.items() if ly==face and u not in mine|retired and c.by_id[u].GetNetname()!=n]+([replacement] if face=='B.Cu' and n!='/CLR_N' else [])) for n in nets}
    for angle in [0,90,180,270]:
        part=pcb.FOOTPRINT(f);part.SetOrientationDegrees(angle)
        body,yard=fab(part),outline(part,yard_layer)
        gd=rotate(guard,-(angle-angle0),origin=origin)
        pads={p.GetNumber():(p.GetNetname(),shape(p,c.ids[face]),xy(p.GetPosition())) for p in part.Pads()}
        for pos in positions:
            dx,dy=pos[0]-origin[0],pos[1]-origin[1]
            bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
            if bo.intersection(bodies).area>1e-8 or ya.intersection(yards).area>1e-8 or ya.intersection(mounts).area>1e-8:
                reject[face+':body_courtyard_mount']+=1;continue
            if ya.intersection(pth_lands).area>1e-8:
                reject[face+':PTH_inside_courtyard']+=1;continue
            pp={k:(n,translate(s,xoff=dx,yoff=dy),(pt[0]+dx,pt[1]+dy)) for k,(n,s,pt) in pads.items()}
            if not box(.5,.5,69.5,34.5).covers(unary_union([bo]+[s for n,s,pt in pp.values()])):
                reject[face+':board_edge']+=1;continue
            if bo.intersects(holes) or any(s.distance(holes)<.299999 for n,s,pt in pp.values()):
                reject[face+':drill_clearance']+=1;continue
            if any(s.distance(vias)<.1999996-1e-9 or s.distance(foreign[n])<.1999996-1e-9 for n,s,pt in pp.values()):
                reject[face+':pad_clearance']+=1;continue
            gg=translate(gd,xoff=dx,yoff=dy)
            if gg.intersection(vias).area>1e-8 or gg.intersection(tracks).area>1e-8:
                reject[face+':native_body_guard']+=1;continue
            if bo.difference(unary_union([s for n,s,pt in pp.values()])).intersection(tracks).area>1e-8:
                reject[face+':same_face_body_trace']+=1;continue
            nrst_distance=math.dist(pp['1'][2],(34.93,26.9))
            rows.append(dict(face=face,position_mm=list(pos),rotation_deg=angle,
               displacement_mm=math.dist(pos,origin),nrst_pad_to_header_mm=nrst_distance,
               pads={k:dict(net=n,position_mm=list(pt)) for k,(n,s,pt) in pp.items()}))
    print(json.dumps(dict(face=face,poses=sum(r['face']==face for r in rows))),flush=True)
rows.sort(key=lambda r:(r['nrst_pad_to_header_mm'],r['displacement_mm']))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,retired_tracks=sorted(retired),
    replacement_clr_spine_mm=[[32.1,13.15],[32.1,13.85]],grid_mm=.5,region_mm=[1.5,1.5,68.5,33.5],
    candidates=rows,rejections=dict(reject),adopted=False),indent=2)+'\n')
print(json.dumps(dict(poses=len(rows),by_face=dict(collections.Counter(r['face'] for r in rows)),best=rows[:10])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
