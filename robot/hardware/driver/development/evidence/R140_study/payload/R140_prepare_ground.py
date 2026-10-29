"""Screen deliberate local ground paths; preserve rejected geometry evidence."""
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
for label,pts in [
 ('initial',[[28.825,15.725],[28.825,15.425],[28.15,14.75],[27.5,14.75],[26.65,15.6],[25.,15.6]]),
 ('clear_U303',[[28.825,15.725],[28.825,15.425],[28.15,14.75],[27.75,14.75],[26.9,15.6],[25.,15.6]])]:
 line=LineString(pts)
 row={'variant':label,'points_mm':pts,'native_obstacles_hit':line.intersects(blocked[0]),'nominal_body_hit':line.intersects(body),'reference_covered':allowed[0].covers(line),'length_mm':line.length,'end_inside_existing_ground':c.copper[('GND','B.Cu')].covers(Point(pts[-1]).buffer(.15))}
 rows.append(row);print(json.dumps(row),flush=True)
 if label=='clear_U303' and not row['native_obstacles_hit'] and not row['nominal_body_hit'] and row['reference_covered'] and row['end_inside_existing_ground']:
  plan={'revision':'R140A','board_sha256':c.sha,'scope':'Independent explicit local C1403 ground bridge into its existing B-face ground area before restoring U303 CLR. No new via, no adoption. Complete native refill and all regressions required.','routes':[{'net':'GND','layer':'B.Cu','width_mm':.3,'points_mm':pts}],'vias':[]}
  f=b/'R140A-plan.json';assert not f.exists();f.write_text(json.dumps(plan,indent=2)+'\n')
f=b/'R140-ground-bridge-screen.json';assert not f.exists();f.write_text(json.dumps({'source_sha256':c.sha,'scope':'Geometric proposal screen only, no PCB changes','variants':rows},indent=2)+'\n')
