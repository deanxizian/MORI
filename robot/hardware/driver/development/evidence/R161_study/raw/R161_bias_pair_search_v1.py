"""Read-only bias-divider pair search with fixed source ground and mechanical holes.
Selects candidates by native geometry and an outward same-face common-node
connection; other copper still needs explicit rerouting and native verification.
"""
import ast,json,math,sys
from pathlib import Path
from shapely.affinity import translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161-bias-pair.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
base=json.loads((b/'R161-compact-group.json').read_text());assert c.sha==base['source_sha256']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fs={f.GetReference():f for f in c.footprints};moving={r['reference'] for r in base['placements']};fixed=[f for f in c.footprints if f.GetReference() not in moving]
for row in base['placements']:
 if row['reference'] in ['R1311','R1312']:continue
 f=pcb.FOOTPRINT(fs[row['reference']]);f.SetPosition(pcb.VECTOR2I(*(round(v*1e6) for v in row['position_mm'])));f.SetOrientationDegrees(row['rotation_deg']);fixed.append(f)
cy_fixed=prep(unary_union([polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in fixed if f.GetLayer()==pcb.B_Cu]))
pad_shapes=[shape(p,pcb.B_Cu) for f in fixed for p in f.Pads() if p.IsOnLayer(pcb.B_Cu)]
ground=unary_union([shape(v,pcb.B_Cu) for v in c.vias if v.GetNetname()=='GND'])
holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias if v.GetNetname()=='GND']+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
body_guard=prep(ground.union(holes));pad_guard=prep(unary_union(pad_shapes+[ground]).buffer(.2005).union(holes.buffer(.3005)))
route_guard=prep(unary_union(pad_shapes+[ground]).buffer(.305).union(holes.buffer(.405)))
fixed_bodies=unary_union([fab(f) for f in fixed if f.GetLayer()==pcb.B_Cu]);domains={};geoms={}
grid=set((ix,iy) for xr,yr in [((400,444),(225,290)),((605,690),(125,325))] for ix in range(xr[0],xr[1]+1) for iy in range(yr[0],yr[1]+1))
for ref in ['R1311','R1312']:
 rows=[]
 for angle in [0,90,180,-90]:
  f=pcb.FOOTPRINT(fs[ref]);f.SetPosition(pcb.VECTOR2I(0,0));f.SetOrientationDegrees(angle)
  cy0=polyset(f.GetCourtyard(pcb.B_CrtYd));body0=fab(f);pads0={p.GetNumber():(shape(p,pcb.B_Cu),xy(p.GetPosition())) for p in f.Pads()}
  for ix,iy in sorted(grid):
   x,y=ix/10,iy/10;cy=translate(cy0,xoff=x,yoff=y)
   if not box(.35,.35,69.65,34.65).covers(cy) or cy_fixed.intersects(cy):continue
   body=translate(body0,xoff=x,yoff=y)
   if body_guard.intersects(body):continue
   pads={n:(translate(sh,xoff=x,yoff=y),(x+pos[0],y+pos[1])) for n,(sh,pos) in pads0.items()}
   if any(pad_guard.intersects(sh) for sh,_ in pads.values()):continue
   ident=f'{ref}:{angle}:{ix}:{iy}';row={'id':ident,'reference':ref,'position_mm':[x,y],'rotation_deg':angle,'pads':{n:list(pos) for n,(_,pos) in pads.items()}}
   rows.append(row);geoms[ident]=(cy,body,pads)
 domains[ref]=rows;print(json.dumps({'reference':ref,'poses':len(rows)}),flush=True)
pairs=[]
for a in domains['R1311']:
 cy1,body1,pa=geoms[a['id']];start=pa['1'][1]
 for q in domains['R1312']:
  cy2,body2,pq=geoms[q['id']];end=pq['2'][1]
  if cy1.intersects(cy2) or math.dist(start,end)>4:continue
  lines=[list((start,end)),[start,(start[0],end[1]),end],[start,(end[0],start[1]),end]]
  valid=[]
  for pts in lines:
   pts=[p for i,p in enumerate(pts) if not i or p!=pts[i-1]];line=LineString(pts)
   if route_guard.intersects(line):continue
   lands=pa['1'][0].union(pq['2'][0])
   if line.buffer(.1).difference(lands).intersection(unary_union([fixed_bodies,body1,body2])).area>1e-6:continue
   if line.distance(pa['2'][0])<.3 or line.distance(pq['1'][0])<.3:continue
   valid.append((line.length,pts))
  if not valid:continue
  length,pts=min(valid)
  score=math.dist(pa['2'][1],(68.8,19.925))+.15*math.dist(a['position_mm'],fs['R1311'].GetPosition() and xy(fs['R1311'].GetPosition()))+length
  pairs.append({'score':score,'poses':[a,q],'common_node_route_B_mm':pts,'common_node_length_mm':length})
pairs.sort(key=lambda r:r['score'])
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'candidate_domains':domains,'pair_count':len(pairs),'best_pairs':pairs[:24],'adopted':False},indent=2)+'\n')
print(json.dumps({'pairs':len(pairs),'best':pairs[:2]}),flush=True)
