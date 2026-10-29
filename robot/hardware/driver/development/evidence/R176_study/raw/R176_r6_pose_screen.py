"""Read-only R1706 native pose/clearance screen within the actual 3 mm rule.

Keep all other parts, copper, vias and original rule areas at R176F positions.
Only R1706 pads/owned body are removed from placement obstacles. No dependency
on moving other copper is silently allowed. Results still require native build
and a complete input/supply restoration; placement is not routing feasibility.
"""
import ast,collections,json,math,sys,time
from pathlib import Path
from shapely.affinity import translate,rotate,scale
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R176-r6-poses.json';assert not out.exists()
c=Copper(str(b/'R176F/MORI_Interface_C3.kicad_pcb'));ref='R1706'
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 node=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),name,'exec'))
f=next(f for f in c.footprints if f.GetReference()==ref);origin=xy(f.GetPosition())
tip=next(p for p in c.pads if c.pad_name(p)=='U1701.1');target=xy(tip.GetPosition())
owned=[k for k in c.keepouts if k['name'].startswith('BODY_'+ref+'_')]
guard=unary_union([k['shape'] for k in owned if k['tracks']]);assert not guard.is_empty
excluded={uid(p) for p in f.Pads()};env={}
for face in ['B.Cu','F.Cu']:
 lid=c.ids[face];yardid=pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd
 env[face]=dict(
  body=unary_union([fab(o) for o in c.footprints if o.GetLayer()==lid and o.GetReference()!=ref]),
  yard=unary_union([outline(o,yardid) for o in c.footprints if o.GetLayer()==lid and o.GetReference()!=ref]),
  vias=unary_union([c.shapes[uid(v),face] for v in c.vias]),
  copper=[(c.by_id[u].GetNetname(),s) for (u,ly),s in c.shapes.items() if ly==face and u not in excluded],
  tracks=unary_union([c.shapes[uid(t),face] for t in c.segments if t.GetLayer()==lid]))
rows=[];rejects=collections.Counter();started=time.monotonic()
for face in ['B.Cu','F.Cu']:
 ff=pcb.FOOTPRINT(f);g=guard;angle0=f.GetOrientationDegrees()
 if face!=c.board.GetLayerName(f.GetLayer()):
  ff.Flip(ff.GetPosition(),pcb.FLIP_DIRECTION_LEFT_RIGHT);g=scale(g,xfact=-1,yfact=1,origin=origin);angle0=ff.GetOrientationDegrees()
 for angle in [0,90,180,270]:
  part=pcb.FOOTPRINT(ff);part.SetOrientationDegrees(angle);lid=c.ids[face]
  body=fab(part);yard=outline(part,pcb.B_CrtYd if face=='B.Cu' else pcb.F_CrtYd)
  gg=rotate(g,-(angle-angle0),origin=origin)
  pads={p.GetNumber():(p.GetNetname(),shape(p,lid),xy(p.GetPosition())) for p in part.Pads()}
  foreign={net:unary_union([s for n,s in env[face]['copper'] if n!=net]) for net,_,_ in pads.values()}
  for xi in range(320,401):
   for yi in range(80,145):
    pos=(xi/8,yi/8);dx=pos[0]-origin[0];dy=pos[1]-origin[1]
    actual={pin:(net,translate(s,xoff=dx,yoff=dy),(pp[0]+dx,pp[1]+dy)) for pin,(net,s,pp) in pads.items()}
    d=math.dist(actual['2'][2],target)
    if d>3+1e-8:rejects['critical_3mm']+=1;continue
    bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy);gd=translate(gg,xoff=dx,yoff=dy)
    if ya.intersection(env[face]['yard']).area>1e-8 or bo.intersection(env[face]['body']).area>1e-8:rejects['part_envelope']+=1;continue
    if gd.intersection(env[face]['vias']).area>1e-8:rejects['native_via_guard']+=1;continue
    if any(s.distance(env[face]['vias'])<.1999996-1e-9 or s.distance(foreign[net])<.1999996-1e-9 for net,s,_ in actual.values()):rejects['pad_clearance']+=1;continue
    lands=unary_union([s for _,s,_ in actual.values()])
    if gd.intersection(env[face]['tracks']).area>1e-8 or bo.difference(lands).intersection(env[face]['tracks']).area>1e-8:rejects['retained_tracks']+=1;continue
    rows.append(dict(face=face,rotation_deg=angle,position_mm=pos,pads={pin:dict(net=n,position_mm=pp) for pin,(n,_,pp) in actual.items()},input_distance_mm=d))
rows.sort(key=lambda r:(r['face']!='B.Cu',r['input_distance_mm']))
out.write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,grid_mm=.125,reference=ref,target_pad='U1701.1',target_max_mm=3,candidates=rows,rejections=dict(rejects),elapsed_seconds=time.monotonic()-started,adopted=False),indent=2)+'\n')
print(json.dumps(dict(count=len(rows),by_face=dict(collections.Counter(r['face'] for r in rows)),best=rows[:12],elapsed_seconds=time.monotonic()-started)),flush=True)
