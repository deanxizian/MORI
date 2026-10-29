"""Read-only C301 same-face pose comparison, retaining all native lands and vias.
Only explicitly enumerated C301 terminal leads are prospectively replaced.
The existing C301 4 mm screening limit remains. Native trial/refill and all
connections, power and reference checks must follow; this is not qualification.
"""
import ast,collections,json,math,sys
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R180E-C301-pose-screen.json';assert not out.exists()
c=Copper(b/'R180E/MORI_Interface_C3.kicad_pcb')
for name,fn in [('fab','R138_joint_search.py'),('outline','R167_joint_pose_screen.py')]:
 n=next(n for n in ast.parse((b/fn).read_text()).body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[n],type_ignores=[]),name,'exec'))
f=next(f for f in c.footprints if f.GetReference()=='C301');origin=xy(f.GetPosition());angle0=f.GetOrientationDegrees();mine={uid(p) for p in f.Pads()};nets={p.GetNetname() for p in f.Pads()}
retired=set()
owned=[k for k in c.keepouts if k['name'].startswith('BODY_C301_')];trackguard=unary_union([k['shape'] for k in owned if k['tracks']]);vg=unary_union([k['shape'] for k in owned if k['vias']]);fixedcut=trackguard.difference(vg)
assert vg.difference(trackguard).area<1e-8
bodies=unary_union([fab(o) for o in c.footprints if o.GetLayer()==c.ids['B.Cu'] and o.GetReference()!='C301'])
yards=unary_union([outline(o,pcb.B_CrtYd) for o in c.footprints if o.GetLayer()==c.ids['B.Cu'] and o.GetReference()!='C301'])
vias=unary_union([c.shapes[uid(v),'B.Cu'] for v in c.vias])
tracks=unary_union([c.shapes[uid(t),'B.Cu'] for t in c.segments if t.GetLayer()==c.ids['B.Cu'] and uid(t) not in retired])
foreign={n:unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and u not in mine|retired and c.by_id[u].GetNetname()!=n]) for n in nets}
cap=next(p for p in c.pads if c.pad_name(p)=='U301.8');capxy=xy(cap.GetPosition());rows=[];reject=collections.Counter();control=False
for angle in [0,90,180,270]:
 part=pcb.FOOTPRINT(f);part.SetOrientationDegrees(angle)
 body=fab(part);yard=outline(part,pcb.B_CrtYd);gd=rotate(trackguard,-(angle-angle0),origin=origin)
 pads={p.GetNumber():(p.GetNetname(),shape(p,c.ids['B.Cu']),xy(p.GetPosition())) for p in part.Pads()}
 for pos in [(x/8,y/8) for x in range(136,213) for y in range(76,137)]+[origin]:
  dx,dy=pos[0]-origin[0],pos[1]-origin[1]
  pp={k:(n,translate(s,xoff=dx,yoff=dy),(xy_[0]+dx,xy_[1]+dy)) for k,(n,s,xy_) in pads.items()}
  if math.dist(pp['1'][2],capxy)>4+1e-5:reject['bypass_distance']+=1;continue
  bo=translate(body,xoff=dx,yoff=dy);ya=translate(yard,xoff=dx,yoff=dy)
  if bo.intersection(bodies).area>1e-8 or ya.intersection(yards).area>1e-8:reject['package_or_courtyard']+=1;continue
  if any(s.distance(vias)<.1999996-1e-9 or s.distance(foreign[n])<.1999996-1e-9 for n,s,pt in pp.values()):reject['pad_clearance']+=1;continue
  gg=translate(gd,xoff=dx,yoff=dy);vv=gg.difference(fixedcut)
  if vv.intersection(vias).area>1e-8:reject['fixed_via_guard']+=1;continue
  if gg.intersection(tracks).area>1e-8 or bo.difference(unary_union([s for n,s,pt in pp.values()])).intersection(tracks).area>1e-8:reject['retained_tracks']+=1;continue
  if math.dist(pos,origin)<1e-7 and (angle-angle0)%360==0:control=True
  rows.append(dict(position_mm=list(pos),rotation_deg=angle,pads={k:dict(net=n,position_mm=list(pt)) for k,(n,s,pt) in pp.items()},bypass_distance_mm=math.dist(pp['1'][2],capxy),displacement_mm=math.dist(pos,origin)))
rows.sort(key=lambda r:(r['bypass_distance_mm'],r['displacement_mm']))
result=dict(scope=__doc__,source_sha256=c.sha,retired_tracks=sorted(retired),deleted_copper_expected={uid(t):dict(net=t.GetNetname(),layer=c.board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd()))) for t in c.segments if uid(t) in retired},unchanged_pose_control=control,candidates=rows,rejections=dict(reject),adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(retired=len(retired),poses=len(rows),control=control,rejections=dict(reject),best=rows[:12])),flush=True)
assert not control and c.sha==hashlib.sha256(Path(c.path).read_bytes()).hexdigest()
