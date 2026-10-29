"""Read-only diagnosis of native-legal transfers blocked by old-trace reference guard.

Full-stroke reference coverage, native copper/pad/hole/keepout rules and existing
2 mm ground-transition screening remain. ONLY the proxy protecting old reference
under future via antipads is omitted to identify exact old tracks needing a
separate redesign. Every result is INVALID_DIAGNOSTIC, never acceptance. No PCB
is saved, no old track is removed, and no real reference defect is waived.
"""
import json,sys
from pathlib import Path
import numpy as np
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner,mask
base=Path('robot/.state/c3-completion/trials');out=base/'R138C-via-reference-diagnostic';out.mkdir(exist_ok=False)
p=Planner(str(base/'R138C/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu','In3.Cu','F.Cu'],.2);c=p.c
parts_=[s.buffer(.457) for (u,_),s in c.shapes.items() if isinstance(c.by_id[u],pcb.PAD)]
parts_ += [k['shape'].buffer(.257) for k in c.keepouts if k['vias']]
parts_ += [Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6+.307) for v in c.vias]
parts_ += [Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2+.557) for q in c.pads if max(xy(q.GetDrillSize()))>0]
p.via_common=unary_union(parts_)
def fab(f):
 ly=pcb.F_Fab if f.GetLayer()==pcb.F_Cu else pcb.B_Fab;lines=[];polys=[]
 for g in f.GraphicalItems():
  if not isinstance(g,pcb.PCB_SHAPE) or g.GetLayer()!=ly:continue
  a,b=xy(g.GetStart()),xy(g.GetEnd())
  if g.GetShape()==pcb.SHAPE_T_SEGMENT:lines.append(LineString([a,b]))
  elif g.GetShape()==pcb.SHAPE_T_RECT:polys.append(box(min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])))
  elif g.GetShape()==pcb.SHAPE_T_POLY:polys.append(polyset(g.GetPolyShape()))
 return unary_union(polys+list(polygonize(unary_union(lines))))
bodies={ly:unary_union([fab(f) for f in c.footprints if c.board.GetLayerName(f.GetLayer())==ly]) for ly in ['F.Cu','B.Cu']};rows=[]
for net,src,dst in [('/01 {slash} Core/ACT_CURRENT_ADC','R1003.2','J101.7')]:
 gs=p.routing_groups(net);a=next(g for g in gs if src in g['pads']);b=next(g for g in gs if dst in g['pads']);free,vf,blocked,allowed=p.geometry(net)
 for i,ly in enumerate(p.layers):
  if ly in bodies:
   own=unary_union([s for (u,l),s in c.shapes.items() if l==ly and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
   blocked[i]=unary_union([blocked[i],bodies[ly].buffer(.102).difference(own.buffer(-.001))])
 free=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True) for ob,al in zip(blocked,allowed)])
 result=p.solve(a,b,(free,vf,blocked,allowed),600000);hits=[]
 if result['status']=='PROPOSAL':
  for v in result['vias']:
   pt=Point(v['position_mm']);old=[]
   for t in c.segments:
    ly=c.board.GetLayerName(t.GetLayer())
    if t.GetNetname()=='GND' or ly not in REFERENCE:continue
    g=c.shapes[uid(t),ly].intersection(p.ground[REFERENCE[ly]])
    loss=g.intersection(pt.buffer(.655))
    if loss.area>1e-8:old.append({'uuid':uid(t),'net':t.GetNetname(),'layer':ly,'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),'estimated_removed_reference_mm2':loss.area})
   hits.append({'via':v,'old_trace_reference_conflicts':old})
 row={'source_sha256':c.sha,'scope':__doc__,'net':net,'groups':[a['pads'],b['pads']],'acceptance_status':'INVALID_DIAGNOSTIC','result':result,'via_reference_conflicts':hits};rows.append(row)
 (out/'searches.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({'net':net,'acceptance_status':'INVALID_DIAGNOSTIC',**{k:v for k,v in result.items() if k not in ['routes','activate_pth_layers']},'via_reference_conflicts':hits}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
