"""R1701 placement against actual R147G copper, all holes, courtyards and 3 mm LIMIT target; screening only."""
import ast,json,sys,time
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147-threshold-placements.json';assert not out.exists()
c=Copper(b/'R147G/MORI_Interface_C3.kicad_pcb')
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fps={f.GetReference():f for f in c.footprints};f=fps['R1701'];o=xy(f.GetPosition());own={uid(q) for q in f.Pads()};target=Point(45.05,12.35)
foreign=[(g,c.by_id[u].GetNetname()) for (u,ly),g in c.shapes.items() if ly=='B.Cu' and u not in own and c.by_id[u].GetNetname()!='Net-(U1701-LIMIT)']
foreign += [(Point(xy(v.GetPosition())).buffer(v.GetWidth(pcb.B_Cu)/2e6),v.GetNetname()) for v in c.vias]
foreign += [(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2),q.GetNetname()) for q in c.pads if max(xy(q.GetDrillSize()))>0]
courts=prep(unary_union([polyset(g.GetCourtyard(pcb.B_CrtYd)) for g in c.footprints if g.GetLayer()==pcb.B_Cu and g.GetReference()!='R1701']))
bodyblocked=prep(unary_union([g.buffer(.005) for g,n in foreign]));blocked={n:prep(unary_union([g.buffer(.205) for g,net in foreign if net!=n])) for n in ['GND','Net-(U1701-LIMIT)']}
rows=[];start=time.time()
for angle in [0,90,180,270]:
 d=angle-f.GetOrientationDegrees()
 court0=rotate(polyset(f.GetCourtyard(pcb.B_CrtYd)),-d,origin=o);body0=rotate(fab(f),-d,origin=o)
 pads0=[(q.GetNumber(),q.GetNetname(),rotate(c.shapes[uid(q),'B.Cu'],-d,origin=o),rotate(Point(xy(q.GetPosition())),-d,origin=o)) for q in f.Pads()]
 for x in np.arange(40,49.0001,.05):
  for y in np.arange(7,16.0001,.05):
   x,y=round(float(x),4),round(float(y),4);dx,dy=x-o[0],y-o[1]
   limit=translate(next(p[3] for p in pads0 if p[0]=='2'),xoff=dx,yoff=dy)
   if limit.distance(target)>3:continue
   court=translate(court0,xoff=dx,yoff=dy)
   if courts.intersects(court):continue
   pads=[(n,translate(g,xoff=dx,yoff=dy)) for _,n,g,_ in pads0]
   if any(blocked[n].intersects(g) for n,g in pads):continue
   if bodyblocked.intersects(translate(body0,xoff=dx,yoff=dy)):continue
   rows.append({'position_mm':[x,y],'rotation_deg':angle,'limit_distance_mm':limit.distance(target),'pad_centres':{p[0]:list(translate(p[3],xoff=dx,yoff=dy).coords[0]) for p in pads0}})
rows.sort(key=lambda r:r['limit_distance_mm'])
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'placements':rows,'routing':'NOT_TESTED'},indent=2)+'\n');print(json.dumps({'count':len(rows),'best':rows[:20],'seconds':time.time()-start}),flush=True)
