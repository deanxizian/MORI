"""Joint R1701/R1707 screening on R147G, removing only their known replaced B tails; no routing qualification."""
import ast,json,sys,time
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147-sense-pair-placements.json';assert not out.exists()
c=Copper(b/'R147G/MORI_Interface_C3.kicad_pcb');a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');old={uid(t) for t in a.segments}
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fps={f.GetReference():f for f in c.footprints};refs=['R1701','R1707'];own={uid(q) for ref in refs for q in fps[ref].Pads()}
removed={uid(t) for t in c.segments if uid(t) not in old and c.board.GetLayerName(t.GetLayer())=='B.Cu' and t.GetNetname() in ['/WHEEL_VM','Net-(U1701-IN-)','Net-(U1701-LIMIT)']}
foreign=[(g,c.by_id[u].GetNetname()) for (u,ly),g in c.shapes.items() if ly=='B.Cu' and u not in own and u not in removed]
foreign += [(Point(xy(v.GetPosition())).buffer(v.GetWidth(pcb.B_Cu)/2e6),v.GetNetname()) for v in c.vias]
foreign += [(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2),q.GetNetname()) for q in c.pads if max(xy(q.GetDrillSize()))>0]
courts=prep(unary_union([polyset(g.GetCourtyard(pcb.B_CrtYd)) for g in c.footprints if g.GetLayer()==pcb.B_Cu and g.GetReference() not in refs]))
bodyblocked=prep(unary_union([g.buffer(.005) for g,n in foreign]));blocked={n:prep(unary_union([g.buffer(.205) for g,net in foreign if net!=n])) for ref in refs for q in fps[ref].Pads() for n in [q.GetNetname()]}
result={};start=time.time()
for ref,target in [('R1701',Point(45.05,12.35)),('R1707',Point(45.05,12.85))]:
 f=fps[ref];o=xy(f.GetPosition());rows=[]
 for angle in [0,90,180,270]:
  d=angle-f.GetOrientationDegrees()
  court0=rotate(polyset(f.GetCourtyard(pcb.B_CrtYd)),-d,origin=o);body0=rotate(fab(f),-d,origin=o)
  pads0=[(q.GetNumber(),q.GetNetname(),rotate(c.shapes[uid(q),'B.Cu'],-d,origin=o),rotate(Point(xy(q.GetPosition())),-d,origin=o)) for q in f.Pads()]
  for x in np.arange(40,49.0001,.05):
   for y in np.arange(7,16.0001,.05):
    x,y=round(float(x),4),round(float(y),4);dx,dy=x-o[0],y-o[1]
    pin=translate(next(p[3] for p in pads0 if p[0]=='2'),xoff=dx,yoff=dy)
    if pin.distance(target)>3:continue
    court=translate(court0,xoff=dx,yoff=dy)
    if courts.intersects(court):continue
    pads=[(n,translate(g,xoff=dx,yoff=dy)) for _,n,g,_ in pads0]
    if any(blocked[n].intersects(g) for n,g in pads):continue
    if bodyblocked.intersects(translate(body0,xoff=dx,yoff=dy)):continue
    rows.append({'position_mm':[x,y],'rotation_deg':angle,'pin_distance_mm':pin.distance(target),'court':court,'pad_centres':{p[0]:list(translate(p[3],xoff=dx,yoff=dy).coords[0]) for p in pads0}})
  print(ref,angle,'feasible',len(rows),'seconds',round(time.time()-start,1),flush=True)
 result[ref]=rows
pairs=[]
for i,r in enumerate(result['R1701']):
 for j,s in enumerate(result['R1707']):
  if not r['court'].intersects(s['court']):pairs.append({'R1701':i,'R1707':j,'sum_pin_distance_mm':r['pin_distance_mm']+s['pin_distance_mm']})
pairs.sort(key=lambda p:p['sum_pin_distance_mm'])
data={'scope':__doc__,'source_sha256':c.sha,'removed_for_screen':sorted(removed),'placements':{ref:[{k:v for k,v in r.items() if k!='court'} for r in rows] for ref,rows in result.items()},'pairs':pairs}
out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({'counts':{ref:len(rows) for ref,rows in result.items()},'pair_count':len(pairs),'best_pairs':[{**p,'r1':data['placements']['R1701'][p['R1701']],'r7':data['placements']['R1707'][p['R1707']]} for p in pairs[:8]]}),flush=True)
