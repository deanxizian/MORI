"""Read-only R1310 pose screen around the half-turned U1701 in R169B.

Three declared F leads are prospectively replaced; all existing vias remain.
Native clearances, body/courtyard, reference constraints and original guards
are retained. Independent pose proposals do not restore old wiring or qualify
any complete layout. No source board is written.
"""
import ast,json,math,sys,collections
from pathlib import Path
import numpy as np
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.affinity import rotate,translate
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R169-R1310-pose-screen.json';assert not out.exists()
p=Planner(b/'R169B/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c
source_sha='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
assert json.loads((b/'R169B-plan.json').read_text())['board_sha256']==source_sha
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
def outline(f,layer):
 lines=[];polys=[]
 for g in f.GraphicalItems():
  if not isinstance(g,pcb.PCB_SHAPE) or g.GetLayer()!=layer:continue
  a,z=xy(g.GetStart()),xy(g.GetEnd())
  if g.GetShape()==pcb.SHAPE_T_SEGMENT:lines.append(LineString([a,z]))
  elif g.GetShape()==pcb.SHAPE_T_RECT:polys.append(box(min(a[0],z[0]),min(a[1],z[1]),max(a[0],z[0]),max(a[1],z[1])))
  elif g.GetShape()==pcb.SHAPE_T_POLY:polys.append(polyset(g.GetPolyShape()))
 return unary_union(polys+list(polygonize(unary_union(lines))))
fps={f.GetReference():f for f in c.footprints};u=fps['R1310'];origin=xy(u.GetPosition());oldangle=u.GetOrientationDegrees();assert origin==(49.5,14.25) and oldangle==180
removed_tracks={'bcdd7ab3-adde-4d13-afc7-60400ae05dc1','f53097d6-39cd-41f5-a174-4720708ce322','3c59ab5a-ed77-4497-bfe1-918eab519360'}
movable_via=None
excluded_pad_ids={uid(q) for q in u.Pads()};owned=[k for k in c.keepouts if k['name'].startswith('BODY_R1310_')]
assert owned and not any('_VIA_' in k['name'] for k in owned)
foreign_bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.F_Cu and f.GetReference()!='R1310'])
foreign_yards=unary_union([outline(f,pcb.F_CrtYd) for f in c.footprints if f.GetLayer()==pcb.F_Cu and f.GetReference()!='R1310'])
via_lands=unary_union([c.shapes[uid(v),'F.Cu'] for v in c.vias if uid(v)!=movable_via and (uid(v),'F.Cu') in c.shapes])
fixed_ftracks=[t for t in c.segments if c.board.GetLayerName(t.GetLayer())=='F.Cu' and uid(t) not in removed_tracks]
fixed_ftrack_shapes=unary_union([c.shapes[uid(t),'F.Cu'] for t in fixed_ftracks])
fpad_rows=[(q.GetNetname(),c.shapes[uid(q),'F.Cu']) for q in c.pads if uid(q) not in excluded_pad_ids and (uid(q),'F.Cu') in c.shapes]
fnets={q.GetNetname() for q in u.Pads()}
foreign_f={n:unary_union([s for nn,s in fpad_rows if nn!=n]+[c.shapes[uid(t),'F.Cu'] for t in fixed_ftracks if t.GetNetname()!=n]) for n in fnets}
cap=next(q for q in c.pads if c.pad_name(q)=='U1302.4');cap_pos=xy(cap.GetPosition())
net='/FAULT_N';free,_,blocked,allowed=p.geometry(net)
bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu]);lands=unary_union([s for (i,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[i],pcb.PAD) and c.by_id[i].GetNetname()==net])
blocked[0]=blocked[0].union(bodies.buffer(.102).difference(lands.buffer(-.001)))
free[0]=~mask(blocked[0],p.xx,p.yy)&mask(allowed[0],p.xx,p.yy,True)
pad=next(q for q in c.pads if c.pad_name(q)=='U1701.5');start=mask(c.shapes[uid(pad),'B.Cu'].buffer(-.001),p.xx,p.yy,True)&free[0]
lab,n=ndimage.label(free[0],np.ones((3,3)));region=np.isin(lab,np.unique(lab[start]));assert not np.any(region&~free[0])
ys,xs=np.where(region);xx=p.xx[ys,xs];yy=p.yy[ys,xs]
# Source ground remains conservative after the declared prospective retirement.
referenced=[c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]) for t in c.segments if uid(t) not in removed_tracks and t.GetNetname()!='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE]
via_blocks=[unary_union(referenced).buffer(.657)]
via_blocks.extend(s.buffer(.457) for (i,l),s in c.shapes.items() if isinstance(c.by_id[i],pcb.PAD) and i not in excluded_pad_ids)
via_blocks.extend(k['shape'].buffer(.257) for k in c.keepouts if k['vias'] and k not in owned)
via_blocks.extend(Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias if uid(v)!=movable_via)
via_blocks.extend(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0)
via_blocks.extend(s.buffer(.457) for (i,l),s in c.shapes.items() if c.by_id[i].GetNetname()!=net and not isinstance(c.by_id[i],pcb.PAD) and i not in removed_tracks and i!=movable_via)
base_eligible=~mask(unary_union(via_blocks),xx,yy)
inner_eligible=(free[3][ys,xs]|(free[2][ys,xs]&p.ground_near[ys,xs]))
base_eligible &= inner_eligible
print('Reachable B points',len(xs),'eligible before relocated R1310 pads/guards',int(base_eligible.sum()),flush=True)
rejected=collections.Counter();poses=[]
for dx in [i*.25 for i in range(-8,13)]:
 for dy in [i*.25 for i in range(-6,7)]:
  for angle in [0,90,180,270]:
   f=pcb.FOOTPRINT(u);f.SetOrientationDegrees(angle);f.SetPosition(pcb.VECTOR2I(round((origin[0]+dx)*1e6),round((origin[1]+dy)*1e6)))
   body=fab(f);yard=outline(f,pcb.F_CrtYd);pp=[(q.GetNumber(),q.GetNetname(),shape(q,pcb.F_Cu),xy(q.GetPosition())) for q in f.Pads()]
   if body.intersection(foreign_bodies).area>1e-8:rejected['body']+=1;continue
   if yard.intersection(foreign_yards).area>1e-8:rejected['courtyard']+=1;continue
   if any(s.distance(via_lands)<.2-1e-6 for _,_,s,_ in pp):rejected['fixed_via_pad']+=1;continue
   if any(s.distance(foreign_f[n])<.2-1e-6 for _,n,s,_ in pp):rejected['pad_or_retained_track']+=1;continue
   transformed=[dict(k,shape=translate(rotate(k['shape'],-(angle-oldangle),origin=origin),xoff=dx,yoff=dy)) for k in owned]
   if any(k['vias'] and k['shape'].intersects(via_lands) for k in transformed):rejected['native_guard_fixed_vias']+=1;continue
   if any(k['tracks'] and 'F.Cu' in k['layers'] and k['shape'].intersects(fixed_ftrack_shapes) for k in transformed):rejected['native_guard_retained_tracks']+=1;continue
   bypass=math.dist(cap_pos,next(q[3] for q in pp if q[0]=='1'))
   if bypass>4+1e-9:rejected['bypass_distance']+=1;continue
   blocks=unary_union([s.buffer(.457) for _,_,s,_ in pp]+[k['shape'].buffer(.257) for k in transformed if k['vias']])
   good=base_eligible&~mask(blocks,xx,yy)
   positions=[[round(float(x),6),round(float(y),6)] for x,y in zip(xx[good],yy[good])];positions.sort(key=lambda q:math.dist(q,xy(pad.GetPosition())))
   old_via_contact=False
   poses.append(dict(position_mm=[origin[0]+dx,origin[1]+dy],rotation_deg=angle,delta_mm=[dx,dy],CT_pin_distance_mm=bypass,legal_port_grid_points=len(positions),port_examples_mm=positions[:12],requires_source_via_relocation=old_via_contact,score=math.hypot(dx,dy)+min((angle-oldangle)%360,(oldangle-angle)%360)/180))
poses.sort(key=lambda r:(not bool(r['legal_port_grid_points']),r['score'],-r['legal_port_grid_points']))
result=dict(scope=__doc__,canonical_source_sha256=source_sha,geometry_source_sha256=c.sha,U1701_pose=dict(position_mm=[47.25,12.35],rotation_deg=180),all_source_vias_unchanged=True,prospectively_replaced_R1310_F_tracks=sorted(removed_tracks),prospectively_movable_non_ground_via=movable_via,reachable_B_grid_points=len(xs),eligible_before_moved_R1310=int(base_eligible.sum()),rejections=dict(rejected),poses=poses,adopted=False,native_DRC='NOT_TESTED')
out.write_text(json.dumps(result,indent=2)+'\n');print('Placement candidates',len(poses),'with ports',sum(bool(r['legal_port_grid_points']) for r in poses),flush=True)
for r in poses[:5]:print(json.dumps(r),flush=True)
