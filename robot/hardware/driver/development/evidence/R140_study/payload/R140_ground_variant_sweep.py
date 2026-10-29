"""Bounded deliberate-bend comparison for the local C1403 ground bridge."""
import sys,json,ast
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_layered_route import Planner
b=Path('robot/.state/c3-completion/trials')
p=Planner(str(b/'R139K/MORI_Interface_C3.kicad_pcb'),.05,['B.Cu'],.3);c=p.c
node=next(x for x in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
_,_,blocked,allowed=p.geometry('GND')
bodies=unary_union([fab(f) for f in c.footprints if f.GetLayer()==pcb.B_Cu])
own=unary_union([s for (u,l),s in c.shapes.items() if l=='B.Cu' and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()=='GND'])
body=bodies.buffer(.152).difference(own.buffer(-.001))
rows=[]
for y in [14.65,14.7,14.75,14.8,14.85]:
 for x in [27.55,27.575,27.6,27.625,27.65,27.675,27.7,27.725,27.75]:
  for end_y in [15.5,15.55,15.6,15.65,15.7]:
   pts=[[28.825,15.725],[28.825,round(y+.675,6)],[28.15,y],[x,y],[round(x-(end_y-y),6),end_y],[25.,end_y]]
   line=LineString(pts)
   row={'points_mm':pts,'obstacle':line.intersects(blocked[0]),'body':line.intersects(body),'reference':allowed[0].covers(line),'end_ground':c.copper[('GND','B.Cu')].covers(Point(pts[-1]).buffer(.15)),'length_mm':line.length}
   rows.append(row)
good=[r for r in rows if not r['obstacle'] and not r['body'] and r['reference'] and r['end_ground']]
if good:
 # Maximize geometric margin after satisfying every check; no clearance waiver.
 for r in good:
  line=LineString(r['points_mm']);r['screen_margin_mm']=min(line.distance(blocked[0]),line.distance(body),line.distance(allowed[0].boundary))
 chosen=max(good,key=lambda r:r['screen_margin_mm'])
 plan={'revision':'R140A','board_sha256':c.sha,'scope':'Independent explicit local C1403 GND bridge, 0.30 mm; deliberate 45-degree bends preserve native clearance and reference coverage. Connect to existing ground area before restoring CLR. Full native acceptance required; not adopted.','routes':[{'net':'GND','layer':'B.Cu','width_mm':.3,'points_mm':chosen['points_mm']}],'vias':[]}
 f=b/'R140A-plan.json';assert not f.exists();f.write_text(json.dumps(plan,indent=2)+'\n')
else:chosen=None
f=b/'R140-ground-variant-screen.json';assert not f.exists();f.write_text(json.dumps({'source_sha256':c.sha,'scope':__doc__,'variants':rows,'chosen':chosen},indent=2)+'\n')
print(json.dumps({'variants':len(rows),'passing':len(good),'chosen':chosen}),flush=True)
