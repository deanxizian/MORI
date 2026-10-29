"""Finite C1403 relocation study against R143O, with main-ground attachment.

Remove only the moving capacitor, its owned body guards and explicitly named
old ground bridge/cap stub from virtual geometry. Restore candidate pads/body
for each route. A proposal is not adoption; native refill and full regression
remain mandatory. No source file is saved.
"""
import ast, json, math, sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups
import plan_layered_route as module
from plan_layered_route import mask

base=Path('robot/.state/c3-completion/trials')
out=base/'R144-cap-placements.json'; assert not out.exists()
source=base/'R143O/MORI_Interface_C3.kicad_pcb'
c0=Copper(str(source))
drop=['14120b5b-7296-5ca1-8603-a552ee726c3a','19587ce5-3c49-5ebb-ae07-bd327a55b4a6','48e31730-5a96-5ecf-b5a6-24b48806bbf7','58ea3a09-d899-5fae-941a-d37413cd5fb7','85ab00d9-cd16-5168-809b-4bc67e1aaf18','8c3dc0c6-a03f-5973-b986-4d670f9faa1b','f9561527-62f3-5994-8918-97c72ee3e4f6','da708e42-96e3-4cdd-9cfb-32b1fffdb3d9']
assert all(u in c0.by_id for u in drop)
def virtual(path):
 c=Copper(path)
 mine={uid(q) for f in c.footprints if f.GetReference()=='C1403' for q in f.Pads()}|set(drop)
 c.footprints=[f for f in c.footprints if f.GetReference()!='C1403']
 c.pads=[q for q in c.pads if uid(q) not in mine]
 c.items=[q for q in c.items if uid(q) not in mine]
 c.tracks=[q for q in c.tracks if uid(q) not in mine]
 c.segments=[q for q in c.segments if uid(q) not in mine]
 c.by_id={u:q for u,q in c.by_id.items() if u not in mine}
 c.zones=[z for z in c.zones if not(z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_C1403_'))]
 return c
module.Copper=virtual
p=module.Planner(str(source),.05,['B.Cu'],.2);c=p.c
node=next(n for n in ast.parse((base/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
f=next(f for f in c0.footprints if f.GetReference()=='C1403')
origin=xy(f.GetPosition());angle0=f.GetOrientationDegrees();pads=list(f.Pads())
court=polyset(f.GetCourtyard(pcb.B_CrtYd));body=fab(f)
main=next(g['layers']['B.Cu'] for g in groups(c0,'GND') if 'U1401.2' in g['pads'])
others=unary_union([polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in c.footprints if f.GetLayer()==pcb.B_Cu])
others=others.union(unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('MOUNT_') and 'B.Cu' in k['layers']]))
via=prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PCB_VIA)]))
foreign={q.GetNetname():prep(unary_union([s.buffer(.205) for (u,ly),s in c.shapes.items() if ly=='B.Cu' and c.by_id[u].GetNetname()!=q.GetNetname()])) for q in pads}
old_traces=unary_union([c.shapes[uid(t),'B.Cu'] for t in c.segments if t.GetLayer()==pcb.B_Cu])
net=next(q.GetNetname() for q in pads if q.GetNumber()=='1')
free,vf,blocked,allowed=p.geometry(net)
lands=unary_union([s for (u,ly),s in c.shapes.items() if ly=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==net])
bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu])
blocked[0]=unary_union([blocked[0],bodies.buffer(.102).difference(lands.buffer(-.001))])
seed=next(g for g in p.routing_groups(net) if 'U1401.3' in g['pads'])
rows=[]
for angle in [0,90,180,270]:
 for y in np.arange(14,23.001,.1):
  for x in np.arange(21,34.001,.1):
   def tr(g):return translate(rotate(g,-(angle-angle0),origin=origin),xoff=x-origin[0],yoff=y-origin[1])
   ct=tr(court)
   if ct.buffer(.01).intersects(others):continue
   pp={q.GetNumber():tr(c0.shapes[uid(q),'B.Cu']) for q in pads}
   if any(foreign[q.GetNetname()].intersects(pp[q.GetNumber()]) or via.intersects(pp[q.GetNumber()]) for q in pads):continue
   if pp['2'].intersection(main).area<.1:continue
   bd=tr(body)
   if bd.intersects(old_traces):continue
   rows.append({'position_mm':[round(float(x),3),round(float(y),3)],'angle_deg':angle,'pads_mm':{n:[round(g.centroid.x,6),round(g.centroid.y,6)] for n,g in pp.items()},'score':Point(x,y).distance(Point(28.6125,19.3)),'ground_overlap_mm2':pp['2'].intersection(main).area})
 print(json.dumps({'angle':angle,'cumulative_preliminary_positions':len(rows)}),flush=True)
rows.sort(key=lambda r:r['score']);checked=[];results=[]
for row in rows:
 if any(math.dist(row['position_mm'],r['position_mm'])<.5 and row['angle_deg']==r['angle_deg'] for r in checked):continue
 checked.append(row)
 if len(checked)>24:break
 x,y=row['position_mm'];angle=row['angle_deg']
 def tr(g):return translate(rotate(g,-(angle-angle0),origin=origin),xoff=x-origin[0],yoff=y-origin[1])
 pp={q.GetNumber():tr(c0.shapes[uid(q),'B.Cu']) for q in pads}
 ob=unary_union([blocked[0],pp['2'].buffer(.305),tr(body).buffer(.102).difference(pp['1'].buffer(-.001))])
 al=allowed[0].union(pp['1'].buffer(-.102))
 fr=np.array([~mask(ob,p.xx,p.yy)&mask(al,p.xx,p.yy,True)])
 r=p.solve(seed,{'pads':['C1403.1'],'layers':{'B.Cu':pp['1']}},(fr,np.zeros(vf.shape,dtype=bool),[ob],[al]),150000)
 results.append({'pose':row,'result':r});print(json.dumps(results[-1]),flush=True)
 if r.get('status')=='PROPOSAL' and r.get('length_mm',100)<6:break
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c0.sha,'virtual_removed_tracks':drop,'preliminary_positions':rows,'routes':results},indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==c0.sha
