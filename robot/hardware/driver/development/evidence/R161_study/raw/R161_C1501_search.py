"""Place the U1501 input capacitor near its input while preserving nearby copper.
Includes PTH/courtyard, all pad-to-via spacing and explicit local B-side path.
No candidate is adopted by this bounded geometric screen.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161-C1501-search.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
g=json.loads((b/'R161-Cgroup-v2.json').read_text());assert c.sha==g['source_sha256']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fs={f.GetReference():f for f in c.footprints};moving={r['reference'] for r in g['placements']}
fixed=[f for f in c.footprints if f.GetReference() not in moving]
for r in g['placements']:
 if r['reference']=='C1501':continue
 f=pcb.FOOTPRINT(fs[r['reference']]);f.SetPosition(pcb.VECTOR2I(*(round(x*1e6) for x in r['position_mm'])));f.SetOrientationDegrees(r['rotation_deg']);f.BuildCourtyardCaches();fixed.append(f)
cy_guard=prep(unary_union([polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in fixed if f.GetLayer()==pcb.B_Cu]).buffer(.01))
ps=[p for f in fixed for p in f.Pads() if p.IsOnLayer(pcb.B_Cu)]
pth_guard=prep(unary_union([shape(p,pcb.B_Cu) for p in ps if p.GetAttribute()==pcb.PAD_ATTRIB_PTH]).buffer(.005))
vias=unary_union([shape(v,pcb.B_Cu) for v in c.vias]);gv=unary_union([shape(v,pcb.B_Cu) for v in c.vias if v.GetNetname()=='GND'])
holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias]+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in ps if max(xy(p.GetDrillSize()))>0])
body_guard=prep(gv);hole_guard=prep(holes.buffer(.302));pad_guards={}
net='Net-(U1501-INB-_{slash}_OV)';target=(54.4,31.8)
trace_guard=prep(unary_union([c.shapes.get((uid(t),'B.Cu'),GeometryCollection()) for t in c.tracks if t.GetNetname()!=net]+[shape(p,pcb.B_Cu) for p in ps if p.GetNetname()!=net]).buffer(.302))
hole_trace_guard=prep(unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias if v.GetNetname()!=net]+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in ps if p.GetNetname()!=net and max(xy(p.GetDrillSize()))>0]).buffer(.402))
fixed_bodies=unary_union([fab(f) for f in fixed if f.GetLayer()==pcb.B_Cu])
rows=[];tested=0
for ang in [0,90,180,-90]:
 f=pcb.FOOTPRINT(fs['C1501']);f.SetPosition(pcb.VECTOR2I(0,0));f.SetOrientationDegrees(ang);f.BuildCourtyardCaches()
 cy0=polyset(f.GetCourtyard(pcb.B_CrtYd));body0=fab(f);p0={p.GetNumber():(p.GetNetname(),shape(p,pcb.B_Cu),xy(p.GetPosition())) for p in f.Pads()}
 for pn,native,sh in [(p.GetNumber(),p.GetNetname(),shape(p,pcb.B_Cu)) for p in f.Pads()]:
  if native not in pad_guards:pad_guards[native]=prep(vias.union(unary_union([shape(q,pcb.B_Cu) for q in ps if q.GetNetname()!=native])).buffer(.202))
 for ix in range(970,1141):
  for iy in range(550,676):
   x,y=ix/20,iy/20;tested+=1;cy=translate(cy0,xoff=x,yoff=y)
   if cy_guard.intersects(cy) or pth_guard.intersects(cy):continue
   body=translate(body0,xoff=x,yoff=y)
   if body_guard.intersects(body):continue
   pads={n:(nt,translate(sh,xoff=x,yoff=y),(pos[0]+x,pos[1]+y)) for n,(nt,sh,pos) in p0.items()}
   if any(pad_guards[nt].intersects(sh) or hole_guard.intersects(sh) or not box(.505,.505,69.495,34.495).covers(sh) for nt,sh,_ in pads.values()):continue
   start=pads['1'][2];lands=pads['1'][1].union(Point(target).buffer(.25));paths=[]
   for pts in [[start,target],[start,(start[0],target[1]),target],[start,(target[0],start[1]),target]]:
    pts=[p for i,p in enumerate(pts) if not i or p!=pts[i-1]];line=LineString(pts)
    if trace_guard.intersects(line) or hole_trace_guard.intersects(line):continue
    if line.buffer(.1).difference(lands).intersection(body.union(fixed_bodies)).area>1e-6:continue
    paths.append((line.length,pts))
   if not paths:continue
   length,pts=min(paths)
   pending=[]
   for t in c.tracks:
    sh=c.shapes.get((uid(t),'B.Cu'))
    if sh is None:continue
    if body.intersection(sh).area>1e-6 or any(nt!=t.GetNetname() and land.distance(sh)<.202 for nt,land,_ in pads.values()):pending.append({'uuid':uid(t),'net':t.GetNetname(),'via':isinstance(t,pcb.PCB_VIA)})
   if pending:continue
   rows.append({'position_mm':[x,y],'rotation_deg':ang,'pads':{n:{'net':nt,'position_mm':list(pos)} for n,(nt,_,pos) in pads.items()},'route_B_mm':pts,'local_route_length_mm':length})
rows.sort(key=lambda r:r['local_route_length_mm'])
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'tested':tested,'count':len(rows),'best':rows[:30],'adopted':False},indent=2)+'\n')
print(json.dumps({'tested':tested,'count':len(rows),'best':rows[:3]}),flush=True)
