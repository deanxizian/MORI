"""Native-geometry R1706 two-face placement with the other group parts fixed.

Use R173C only for transformed pads, vias, bodies and guards, never its shorted
connectivity. All retained source tracks retain canonical net identities.
Enumerated track conflicts are restoration dependencies; no pad/via/body or
fixed interface conflict is waived. Whole routing/reference checks remain due.
"""
import ast,collections,json,math,sys,time
from pathlib import Path
from shapely.affinity import rotate,translate,scale
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R173-input-resistor-screen.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');a=Copper(b/'R173C/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R173C-plan.json').read_text());retired=set(p['delete_copper'])
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
f=next(f for f in c.footprints if f.GetReference()=='R1706');origin=xy(f.GetPosition());bg=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_R1706_')]);target=next(q for q in a.pads if a.pad_name(q)=='U1701.1');oldangle=f.GetOrientationDegrees()
rows=[];counts={};started=time.monotonic()
for face in ['B.Cu','F.Cu']:
 lid=a.board.GetLayerID(face);yardid=pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd
 bd=unary_union([fab(q) for q in a.footprints if q.GetReference()!='R1706' and q.GetLayer()==lid]);yards=unary_union([outline(q,yardid) for q in a.footprints if q.GetReference()!='R1706' and q.GetLayer()==lid]);vl=unary_union([a.shapes[uid(v),face] for v in a.vias])
 fp={n:unary_union([s for (u,ly),s in a.shapes.items() if ly==face and isinstance(a.by_id[u],pcb.PAD) and a.pad_name(a.by_id[u]).split('.')[0]!='R1706' and a.by_id[u].GetNetname()!=n]) for n in [q.GetNetname() for q in f.Pads()]}
 tracks=[(uid(t),t.GetNetname(),c.shapes[uid(t),face]) for t in c.segments if uid(t) not in retired and t.GetLayer()==lid]
 newtracks=[(r['net'],LineString(r['points_mm']).buffer(r['width_mm']/2)) for r in p['routes'] if r['layer']==face]
 template=pcb.FOOTPRINT(f);guard=bg;angle0=oldangle
 if face=='F.Cu':template.Flip(template.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT);angle0=template.GetOrientationDegrees();guard=scale(bg,xfact=-1,yfact=1,origin=origin)
 reject=collections.Counter()
 for x in [v/8 for v in range(320,425)]:
  for y in [v/8 for v in range(56,145)]:
   for angle in [0,90,180,270]:
    ff=pcb.FOOTPRINT(template);ff.SetOrientationDegrees(angle);ff.SetPosition(pcb.VECTOR2I(round(x*1e6),round(y*1e6)))
    pp=[(q.GetNumber(),q.GetNetname(),shape(q,lid),xy(q.GetPosition())) for q in ff.Pads()];distance=math.dist(next(q[3] for q in pp if q[0]=='2'),xy(target.GetPosition()))
    if distance>4:continue
    body=fab(ff);yard=outline(ff,yardid)
    if yard.intersection(yards).area>1e-8 or body.intersection(bd).area>1e-8:reject['body_courtyard']+=1;continue
    if any(s.distance(vl)<.2-1e-6 for _,_,s,_ in pp):reject['via_pad']+=1;continue
    if any(s.distance(fp[n])<.2-1e-6 for _,n,s,_ in pp):reject['foreign_pad']+=1;continue
    tg=translate(rotate(guard,-(angle-angle0),origin=origin),xoff=x-origin[0],yoff=y-origin[1])
    if tg.intersects(vl):reject['native_via_guard']+=1;continue
    if any(body.intersection(s).area>1e-8 or any(n!=pn and s.distance(ps)<.2-1e-6 for _,pn,ps,_ in pp) for n,s in newtracks):reject['new_restore_track']+=1;continue
    deps=[u for u,n,s in tracks if body.difference(unary_union([p[2] for p in pp])).intersection(s).area>1e-8 or tg.intersects(s) or any(n!=pn and s.distance(ps)<.2-1e-6 for _,pn,ps,_ in pp)]
    if len(deps)>5:continue
    rows.append(dict(face=face,position_mm=[x,y],rotation_deg=angle,input_distance_mm=distance,pads={q[0]:dict(net=q[1],position_mm=list(q[3])) for q in pp},additional_track_dependencies=sorted(deps),score=8*len(deps)+distance+.5*(face=='F.Cu')))
 counts[face]=dict(reject);print(json.dumps(dict(face=face,poses=sum(r['face']==face for r in rows),elapsed_seconds=time.monotonic()-started)),flush=True)
rows.sort(key=lambda r:r['score']);out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,candidate_geometry_sha256=a.sha,grid_mm=.125,input_endpoint_bound_mm=4,rejections=counts,poses=rows,adopted=False),indent=2)+'\n')
for r in rows[:12]:print(json.dumps(r),flush=True)
