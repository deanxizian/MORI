"""Read-only diagnosis of original-orientation FAULT port dependencies.

Use R169C only as a declared LIMIT-retirement comparison. Ignore NO rule in an
accepted route: the provisional candidates below separately list every retained
track or reference conflict that would require an explicit replacement plan.
Pads, original via positions, native via keepouts and hole constraints remain.
"""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
from scipy import ndimage
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
b=Path('robot/.state/c3-completion/trials');out=b/'R170-original-port-dependencies.json';assert not out.exists()
p=Planner(b/'R169C/MORI_Interface_C3.kicad_pcb',.05,['B.Cu','F.Cu','In2.Cu','In3.Cu'],.2);c=p.c;net='/FAULT_N'
n=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[n],type_ignores=[]),'fab','exec'))
f,vf,ob,al=p.geometry(net);body=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu]);lands=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net]);ob[0]=ob[0].union(body.buffer(.102).difference(lands.buffer(-.001)));free=~mask(ob[0],p.xx,p.yy)&mask(al[0],p.xx,p.yy,True);pad=next(q for q in c.pads if c.pad_name(q)=='U1701.5');start=mask(c.shapes[uid(pad),'B.Cu'].buffer(-.001),p.xx,p.yy,True)&free;lab,_=ndimage.label(free,np.ones((3,3)));region=np.isin(lab,np.unique(lab[start]));ys,xs=np.where(region);xx=p.xx[ys,xs];yy=p.yy[ys,xs]
physical=[s.buffer(.457) for (u,ly),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD)]
physical += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
physical += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
physical += [s.buffer(.457) for (u,ly),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PCB_VIA) and c.by_id[u].GetNetname()!=net]
physical += [Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0]
eligible=~mask(unary_union(physical),xx,yy);pts=[(round(float(x),6),round(float(y),6)) for x,y in zip(xx[eligible],yy[eligible])];print('reachable',len(xs),'physically eligible absent retained track/reference conflicts',len(pts),flush=True)
ref_shapes={uid(t):c.shapes[uid(t),c.board.GetLayerName(t.GetLayer())].intersection(p.ground[REFERENCE[c.board.GetLayerName(t.GetLayer())]]).buffer(.657) for t in c.segments if t.GetNetname()!='GND' and c.board.GetLayerName(t.GetLayer()) in REFERENCE}
rows=[]
for pos in pts:
 point=Point(pos);blocked=[]
 for t in c.segments:
  if t.GetNetname()==net:continue
  ly=c.board.GetLayerName(t.GetLayer());physical_hit=c.shapes[uid(t),ly].buffer(.457).intersects(point);ref_hit=uid(t) in ref_shapes and ref_shapes[uid(t)].intersects(point)
  if physical_hit or ref_hit:blocked.append(dict(uuid=uid(t),net=t.GetNetname(),layer=ly,width_mm=t.GetWidth()/1e6,physical_copper_conflict=physical_hit,old_reference_conflict=ref_hit,start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd()))))
 rows.append(dict(position_mm=pos,retained_tracks_requiring_review=len(blocked),direct_pad_distance_mm=point.distance(Point(xy(pad.GetPosition()))),conflicts=blocked))
rows.sort(key=lambda r:(r['retained_tracks_requiring_review'],r['direct_pad_distance_mm']))
result=dict(scope=__doc__,canonical_source_sha256='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e',comparison_sha256=c.sha,reachable_B_points=len(xs),physical_only_provisional_points=len(pts),candidates=rows,adopted=False)
out.write_text(json.dumps(result,indent=2)+'\n')
for r in rows[:12]:print(json.dumps(r),flush=True)
