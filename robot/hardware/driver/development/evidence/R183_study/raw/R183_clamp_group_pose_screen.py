"""Bounded D301/D1602 reset/clamp placement study, not a native layout.

Only enumerated diode-terminal branches and their two non-ground transfer vias
are prospectively released. Both diode circuits must be completely restored.
All 114 ground vias, fixed interfaces, other footprints and 5 mm clamp limits
remain. No native source file or manufacturing data is written.
"""
import ast,collections,json,math,sys
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R183-clamp-group-pose-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
    node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
    exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
retired={
 'a64ead90-f8fb-47e5-9d8d-700e6f43096f',
 '8671d9d7-3150-5393-b7e6-7c6081416e91','90ad3b62-8049-5910-bfa9-f24b43746fe0',
 '2795e802-a488-52b5-b92c-f74b09928846','cf85c155-6428-55c0-b7a6-57318be5bc72',
 '2aeed45f-2242-4e5f-8fa4-b5db9d043af0','a0657306-b586-4a43-ba9b-1420b6ca8cbc',
 '7478083b-720e-432e-b578-7ff96fb635be','b3df3a5f-bf2e-4e8c-b2e7-0a565e4fbacc',
 'f5dc0838-1dc6-5fae-9fc1-98f62e18ea5a','fe3d693d-a0e3-4a0f-b828-8806631c7282',
 'ce5760a2-7b20-562c-b64b-90266e7736e7','e3cd7dea-c164-52da-8830-21f7be6a7b38',
 'd80f383a-f21e-46d2-b3b9-aaa3637e14ac','ab82b1cb-be22-4f90-a4ca-3be946bbf2ec',
 '4e37213c-d558-462a-b1fe-290b06cd18d4'}
released_vias={'23acab6c-6b1d-4c9d-9d27-5582d4cb9302','48a80751-1835-4880-839b-49e61af8d8d1'}
assert all(u in c.by_id and not isinstance(c.by_id[u],pcb.PCB_VIA) for u in retired)
assert all(isinstance(c.by_id[u],pcb.PCB_VIA) and c.by_id[u].GetNetname()=='/16 {slash} Actuator_Direct_Switch/ACT_FET_SOURCE' for u in released_vias)
for u in retired:
    assert c.by_id[u].GetNetname() in ['/CLR_N','/16 {slash} Actuator_Direct_Switch/ACT_GATE','/16 {slash} Actuator_Direct_Switch/ACT_FET_SOURCE']
replacement=LineString([(32.1,13.15),(32.1,13.85)]).buffer(.1)
released_refs={'D301','D1602'};mine={uid(p) for f in c.footprints if f.GetReference() in released_refs for p in f.Pads()}
f=next(f for f in c.footprints if f.GetReference()=='D1602');origin=xy(f.GetPosition());angle0=f.GetOrientationDegrees()
targets={k:xy(next(p for p in c.pads if c.pad_name(p)==name).GetPosition()) for k,name in [('1','U1601.6'),('2','U1601.8')]}
owned=[k for k in c.keepouts if k['name'].startswith('BODY_D1602_')]
tg=unary_union([k['shape'] for k in owned if k['tracks']]);vg=unary_union([k['shape'] for k in owned if k['vias']]);fixedcut=tg.difference(vg)
assert vg.difference(tg).area<1e-8
bodies=unary_union([fab(o) for o in c.footprints if o.GetLayer()==pcb.B_Cu and o.GetReference() not in released_refs])
yards=unary_union([outline(o,pcb.B_CrtYd) for o in c.footprints if o.GetLayer()==pcb.B_Cu and o.GetReference() not in released_refs])
mounts=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']])
pth=unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetAttribute()==pcb.PAD_ATTRIB_PTH])
holes=unary_union([Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
vias=unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PCB_VIA) and u not in released_vias])
tracks=unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PCB_TRACK) and not isinstance(c.by_id[u],pcb.PCB_VIA) and u not in retired]+[replacement])
nets={p.GetNetname() for p in f.Pads()}
foreign={n:unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in mine|retired|released_vias and c.by_id[u].GetNetname()!=n]+[replacement]) for n in nets}
positions=[(x/8,y/8) for x in range(248,345) for y in range(80,149)]+[origin]
rows=[];reject=collections.Counter()
for angle in range(0,360,45):
    part=pcb.FOOTPRINT(f);part.SetOrientationDegrees(angle)
    body,yard=fab(part),outline(part,pcb.B_CrtYd);gd=rotate(tg,-(angle-angle0),origin=origin)
    pads={p.GetNumber():(p.GetNetname(),shape(p,c.ids['B.Cu']),xy(p.GetPosition())) for p in part.Pads()}
    for pos in positions:
        dx,dy=pos[0]-origin[0],pos[1]-origin[1]
        pp={k:(n,translate(s,xoff=dx,yoff=dy),(pt[0]+dx,pt[1]+dy)) for k,(n,s,pt) in pads.items()}
        distances={k:math.dist(pt,targets[k]) for k,(n,s,pt) in pp.items()}
        if max(distances.values())>5+1e-7:reject['unchanged_5mm_clamp_limit']+=1;continue
        bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
        if bo.intersection(bodies).area>1e-8 or ya.intersection(yards).area>1e-8 or ya.intersection(mounts).area>1e-8:
            reject['body_courtyard_mount']+=1;continue
        if ya.intersection(pth).area>1e-8:
            reject['PTH_inside_courtyard']+=1;continue
        if bo.intersects(holes) or any(s.distance(holes)<.299999 for n,s,pt in pp.values()):
            reject['drill_clearance']+=1;continue
        if any(s.distance(vias)<.1999996-1e-9 or s.distance(foreign[n])<.1999996-1e-9 for n,s,pt in pp.values()):
            reject['pad_clearance']+=1;continue
        gg=translate(gd,xoff=dx,yoff=dy)
        if gg.difference(fixedcut).intersection(vias).area>1e-8 or gg.intersection(tracks).area>1e-8:
            reject['native_body_guard']+=1;continue
        if bo.difference(unary_union([s for n,s,pt in pp.values()])).intersection(tracks).area>1e-8:
            reject['same_face_body_trace']+=1;continue
        rows.append(dict(position_mm=list(pos),rotation_deg=angle,displacement_mm=math.dist(pos,origin),
            clamp_distances_mm=distances,pads={k:dict(net=n,position_mm=list(pt)) for k,(n,s,pt) in pp.items()}))
    print(json.dumps(dict(angle=angle,poses=sum(p['rotation_deg']==angle for p in rows))),flush=True)
rows.sort(key=lambda r:(max(r['clamp_distances_mm'].values()),r['displacement_mm']))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,released_refs=sorted(released_refs),
    prospective_retired_tracks=sorted(retired),prospective_released_non_ground_vias=sorted(released_vias),
    grid_mm=.125,angles_deg=list(range(0,360,45)),clamp_limit_mm=5,candidates=rows,rejections=dict(reject),adopted=False),indent=2)+'\n')
print(json.dumps(dict(poses=len(rows),rejections=dict(reject),best=rows[:10])),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
