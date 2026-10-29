"""Find a short same-F-side C1301 path to the actual UV input transfer.
Preserve E copper, native footprints, all vias, PTHs, fixed courtyards and
keepouts. This bounded geometry screen is not native refill/DRC acceptance.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161-filter-search.json';assert not out.exists()
c=Copper(str(b/'R161E/MORI_Interface_C3.kicad_pcb'))
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fs={f.GetReference():f for f in c.footprints};fixed=[f for f in c.footprints if f.GetReference()!='C1301']
cy_guard=prep(unary_union([polyset(f.GetCourtyard(pcb.F_CrtYd)) for f in fixed if f.GetLayer()==pcb.F_Cu]).buffer(.01))
ps=[p for f in fixed for p in f.Pads() if p.IsOnLayer(pcb.F_Cu)]
pth_guard=prep(unary_union([shape(p,pcb.F_Cu) for p in ps if p.GetAttribute()==pcb.PAD_ATTRIB_PTH]).buffer(.005))
vias=unary_union([shape(v,pcb.F_Cu) for v in c.vias]);body_guard=prep(vias)
holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias]+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in ps if max(xy(p.GetDrillSize()))>0])
hole_guard=prep(holes.buffer(.302));pad_guards={}
net='Net-(U1301-INA+_{slash}_UV)';target=(62.75,25.25)
fixed_bodies=unary_union([fab(f) for f in fixed if f.GetLayer()==pcb.F_Cu])
trace_ob=unary_union([c.shapes.get((uid(t),'F.Cu'),GeometryCollection()) for t in c.tracks if t.GetNetname()!=net]+[shape(p,pcb.F_Cu) for p in ps if p.GetNetname()!=net]).buffer(.302)
ko=unary_union([k['shape'] for k in c.keepouts if 'F.Cu' in k['layers'] and k['tracks'] and not k['name'].startswith('BODY_C1301')]).buffer(.102)
trace_guard=prep(trace_ob.union(ko))
holes_except_target=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias if v.GetNetname()!=net]+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in ps if p.GetNetname()!=net and max(xy(p.GetDrillSize()))>0]).buffer(.402)
hole_trace_guard=prep(holes_except_target)
rows=[];tested=0
for ang in [0,90,180,-90]:
 f=pcb.FOOTPRINT(fs['C1301']);f.SetPosition(pcb.VECTOR2I(0,0));f.SetOrientationDegrees(ang);f.BuildCourtyardCaches()
 cy0=polyset(f.GetCourtyard(pcb.F_CrtYd));body0=fab(f);p0={p.GetNumber():(p.GetNetname(),shape(p,pcb.F_Cu),xy(p.GetPosition())) for p in f.Pads()}
 for nt,sh,pos in p0.values():
  if nt not in pad_guards:pad_guards[nt]=prep(unary_union([vias]+[shape(q,pcb.F_Cu) for q in ps if q.GetNetname()!=nt]+[c.shapes.get((uid(t),'F.Cu'),GeometryCollection()) for t in c.tracks if t.GetNetname()!=nt]).buffer(.202))
 for ix in range(610,686):
  for iy in range(240,291):
   x,y=ix/10,iy/10;tested+=1;cy=translate(cy0,xoff=x,yoff=y)
   if cy_guard.intersects(cy) or pth_guard.intersects(cy):continue
   body=translate(body0,xoff=x,yoff=y)
   if body_guard.intersects(body):continue
   pads={n:(nt,translate(sh,xoff=x,yoff=y),(pos[0]+x,pos[1]+y)) for n,(nt,sh,pos) in p0.items()}
   if any(pad_guards[nt].intersects(sh) or hole_guard.intersects(sh) or not box(.505,.505,69.495,34.495).covers(sh) for nt,sh,_ in pads.values()):continue
   if any(body.intersection(c.shapes.get((uid(t),'F.Cu'),GeometryCollection())).area>1e-6 for t in c.tracks):continue
   start=pads['1'][2];lands=pads['1'][1].union(Point(target).buffer(.25));paths=[]
   for pts in [[start,target],[start,(start[0],target[1]),target],[start,(target[0],start[1]),target]]:
    pts=[p for i,p in enumerate(pts) if not i or p!=pts[i-1]];line=LineString(pts)
    if trace_guard.intersects(line) or hole_trace_guard.intersects(line):continue
    if line.buffer(.1).difference(lands).intersection(body.union(fixed_bodies)).area>1e-6:continue
    paths.append((line.length,pts))
   if paths:
    length,pts=min(paths);rows.append({'position_mm':[x,y],'rotation_deg':ang,'pads':{n:{'net':nt,'position_mm':list(pos)} for n,(nt,_,pos) in pads.items()},'route_F_mm':pts,'length_mm':length})
rows.sort(key=lambda r:r['length_mm'])
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'tested':tested,'feasible':len(rows),'best':rows[:40],'adopted':False},indent=2)+'\n')
print(json.dumps({'tested':tested,'feasible':len(rows),'best':rows[:3]}),flush=True)
