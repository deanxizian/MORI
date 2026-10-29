"""Read-only four-rotation placement screen against actual copper, holes and bodies."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147-cap-placements.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R147A-plan.json').read_text());assert c.sha==p['board_sha256']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
f=next(f for f in c.footprints if f.GetReference()=='C1602');origin=xy(f.GetPosition());owned={uid(q) for q in f.Pads()};removed=set(p['delete_copper'])
# Compare C1602 while retaining the original R1601. Later joint relocation must
# be separately screened, not assumed to create room.
foreign=[]
for (u,ly),g in c.shapes.items():
 if ly!='B.Cu' or u in owned or u in removed:continue
 o=c.by_id[u]
 foreign.append((g,o.GetNetname(),isinstance(o,pcb.PCB_VIA),u))
pad_ob={net:prep(unary_union([g.buffer(.205) for g,n,via,u in foreign if via or n!=net])) for net in ['/UPS_BAT','Net-(U1601-VCAP)']}
native_body=unary_union([k['shape'] for k in c.keepouts if k['name'].startswith('BODY_C1602_')]) if c.keepouts and 'name' in c.keepouts[0] else fab(f)
native_body=fab(f)
# Any copper across the package body or a through hole under the new package
# needs explicit redesign; this screen does not permit it.
body_ob=prep(unary_union([g.buffer(.005) for g,n,via,u in foreign]))
courts=prep(unary_union([polyset(q.GetCourtyard(pcb.B_CrtYd)) for q in c.footprints if q.GetReference()!='C1602' and q.GetLayer()==pcb.B_Cu]))
gatevia=Point(38.15,12.95).buffer(.455)
rows=[]
for angle in [0,90,180,270]:
 delta=angle-f.GetOrientationDegrees()
 court=translate(rotate(polyset(f.GetCourtyard(pcb.B_CrtYd)),-delta,origin=origin),xoff=-origin[0],yoff=-origin[1])
 body=translate(rotate(native_body,-delta,origin=origin),xoff=-origin[0],yoff=-origin[1])
 pads=[(q.GetNumber(),q.GetNetname(),translate(rotate(c.shapes[(uid(q),'B.Cu')],-delta,origin=origin),xoff=-origin[0],yoff=-origin[1])) for q in f.Pads() if (uid(q),'B.Cu') in c.shapes]
 for x in np.arange(34,43.0001,.1):
  for y in np.arange(8,19.0001,.1):
   x,y=round(float(x),4),round(float(y),4)
   cg=translate(court,xoff=x,yoff=y)
   if courts.intersects(cg):continue
   bg=translate(body,xoff=x,yoff=y)
   if body_ob.intersects(bg) or bg.intersects(gatevia):continue
   actual=[(pin,net,translate(g,xoff=x,yoff=y)) for pin,net,g in pads]
   if any(pad_ob[net].intersects(g) or gatevia.intersects(g) for pin,net,g in actual):continue
   rows.append({'position_mm':[x,y],'rotation_deg':angle,'shift_mm':Point(x,y).distance(Point(origin)),'pad_centres_mm':{pin:list(g.centroid.coords[0]) for pin,net,g in actual}})
rows.sort(key=lambda r:r['shift_mm']);out.write_text(json.dumps({'source_sha256':c.sha,'scope':__doc__,'grid_mm':.1,'placements':rows},indent=2)+'\n')
print(json.dumps({'count':len(rows),'nearest':rows[:20]}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
