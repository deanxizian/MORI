"""Read-only R1701 placement comparison with original INA300 orientation.

All source via positions, other parts, native guards, courtyard and pad
clearances remain. Only the original R1701 GND terminal track is prospectively
replaced; every LIMIT and explicit GND connection still requires real routing.
The 3 mm pin-distance gate is an existing project screen, not qualification.
"""
import ast,collections,json,math,sys
from pathlib import Path
from shapely.affinity import translate,rotate,scale
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R170-R1701-pose-screen.json';assert not out.exists();c=Copper(b/'R170B/MORI_Interface_C3.kicad_pcb');fps={f.GetReference():f for f in c.footprints};old=fps['R1701'];origin=xy(old.GetPosition());angle0=old.GetOrientationDegrees();retired={'4da58487-f076-5185-8828-943f5727193f'};padids={uid(p) for p in old.Pads()};own=[k for k in c.keepouts if k['name'].startswith('BODY_R1701_')];assert len(own)==1 and not any('_VIA_' in k['name'] for k in own)
tree=ast.parse((b/'R167_joint_pose_screen.py').read_text())
for name in ['fab','outline']:
 source=ast.parse((b/'R138_joint_search.py').read_text()) if name=='fab' else tree
 node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
foreign_bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and f.GetReference()!='R1701']) for ly in ['F.Cu','B.Cu']}
foreign_yards={ly:unary_union([outline(f,pcb.F_CrtYd if ly=='F.Cu' else pcb.B_CrtYd) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly and f.GetReference()!='R1701']) for ly in ['F.Cu','B.Cu']}
vias={ly:unary_union([c.shapes[uid(v),ly] for v in c.vias if (uid(v),ly) in c.shapes]) for ly in ['F.Cu','B.Cu']}
retained={ly:[t for t in c.segments if c.board.GetLayerName(t.GetLayer())==ly and uid(t) not in retired] for ly in ['F.Cu','B.Cu']}
tracks={ly:unary_union([c.shapes[uid(t),ly] for t in tt]) for ly,tt in retained.items()}
foreign={(ly,net):unary_union([s for (u,l),s in c.shapes.items() if l==ly and u not in padids|retired and not isinstance(c.by_id[u],pcb.PCB_VIA) and c.by_id[u].GetNetname()!=net]) for ly in ['F.Cu','B.Cu'] for net in ['GND','Net-(U1701-LIMIT)']}
limit=next(p for p in c.pads if c.pad_name(p)=='U1701.3');gnd=next(p for p in c.pads if c.pad_name(p)=='U1701.8');rows=[];reject=collections.Counter()
for face in ['B.Cu','F.Cu']:
 for x in [41.75+i*.25 for i in range(29)]:
  for y in [9.25+i*.25 for i in range(26)]:
   for angle in [0,90,180,270]:
    f=pcb.FOOTPRINT(old)
    if face=='F.Cu':f.Flip(f.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT)
    f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)));pp=[(p.GetNumber(),p.GetNetname(),shape(p,c.ids[face]),xy(p.GetPosition())) for p in f.Pads()];lp=next(p[3] for p in pp if p[0]=='2');gp=next(p[3] for p in pp if p[0]=='1');dist=math.dist(lp,xy(limit.GetPosition()))
    if dist>3+1e-9:reject['LIMIT_distance']+=1;continue
    body=fab(f);yard=outline(f,pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd)
    if body.intersection(foreign_bodies[face]).area>1e-8:reject['body']+=1;continue
    if yard.intersection(foreign_yards[face]).area>1e-8:reject['courtyard']+=1;continue
    if any(s.distance(vias[face])<.2-1e-6 for _,_,s,_ in pp):reject['fixed_via_pad']+=1;continue
    if any(s.distance(foreign[face,n])<.2-1e-6 for _,n,s,_ in pp):reject['pad_track_clearance']+=1;continue
    transformed=[]
    for k in own:
     before=scale(k['shape'],xfact=-1,yfact=1,origin=origin) if face=='F.Cu' else k['shape'];a=angle-(180-angle0) if face=='F.Cu' else angle-angle0;g=translate(rotate(before,-a,origin=origin),xoff=x-origin[0],yoff=y-origin[1]);transformed.append(dict(k,shape=g))
    if any(k['vias'] and k['shape'].intersects(vias[face]) for k in transformed):reject['native_via_guard']+=1;continue
    if any(k['tracks'] and k['shape'].intersects(tracks[face]) for k in transformed):reject['native_track_guard']+=1;continue
    if body.difference(unary_union([s for _,_,s,_ in pp])).intersection(tracks[face]).area>1e-8:reject['retained_track_under_new_body']+=1;continue
    rows.append(dict(face=face,position_mm=[x,y],rotation_deg=angle,LIMIT_pad_mm=list(lp),GND_pad_mm=list(gp),LIMIT_distance_mm=dist,ground_pin_distance_mm=math.dist(gp,xy(gnd.GetPosition())),displacement_mm=math.dist([x,y],origin),score=dist+.3*math.dist(gp,xy(gnd.GetPosition()))+.1*math.dist([x,y],origin)))
rows.sort(key=lambda r:r['score']);result=dict(scope=__doc__,comparison_sha256=c.sha,prospectively_retired_tracks=sorted(retired),rejections=dict(reject),poses=rows,adopted=False);out.write_text(json.dumps(result,indent=2)+'\n');print('poses',len(rows),'B',sum(r['face']=='B.Cu' for r in rows),'F',sum(r['face']=='F.Cu' for r in rows));print('reject',dict(reject))
for row in rows[:15]:print(json.dumps(row))
