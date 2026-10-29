"""Joint C1602/R1601 placement screen; exact source copper plus all through holes."""
import ast,json,sys
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import polygonize
from shapely.prepared import prep
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R147-joint-placements.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');p=json.loads((b/'R147A-plan.json').read_text());assert c.sha==p['board_sha256']
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
refs=['C1602','R1601'];fps={f.GetReference():f for f in c.footprints};own={uid(q) for ref in refs for q in fps[ref].Pads()};removed=set(p['delete_copper'])
foreign=[(g,c.by_id[u].GetNetname(),isinstance(c.by_id[u],pcb.PCB_VIA)) for (u,ly),g in c.shapes.items() if ly=='B.Cu' and u not in own and u not in removed]
# Include holes even if the corresponding B land is currently unflashed.
foreign += [(Point(xy(v.GetPosition())).buffer(v.GetWidth(pcb.B_Cu)/2e6),v.GetNetname(),True) for v in c.vias]
foreign += [(Point(xy(q.GetPosition())).buffer(max(xy(q.GetDrillSize()))/2),q.GetNetname(),True) for q in c.pads if max(xy(q.GetDrillSize()))>0]
foreign.append((Point(37.825,12.95).buffer(.25),'/16 {slash} Actuator_Direct_Switch/ACT_GATE',True))
nativecourts=[polyset(f.GetCourtyard(pcb.B_CrtYd)) for f in c.footprints if f.GetLayer()==pcb.B_Cu and f.GetReference() not in refs]
bodyblocked=prep(unary_union([g.buffer(.005) for g,n,v in foreign]));courts=prep(unary_union(nativecourts))
padblocked={n:prep(unary_union([g.buffer(.205) for g,net,via in foreign if via or net!=n])) for ref in refs for q in fps[ref].Pads() for n in [q.GetNetname()]}
def transformed(ref,angle,x,y):
 f=fps[ref];o=xy(f.GetPosition());d=angle-f.GetOrientationDegrees()
 def tf(g):return translate(rotate(g,-d,origin=o),xoff=x-o[0],yoff=y-o[1])
 pads=[(q.GetNetname(),tf(c.shapes[(uid(q),'B.Cu')])) for q in f.Pads() if (uid(q),'B.Cu') in c.shapes]
 return tf(polyset(f.GetCourtyard(pcb.B_CrtYd))),tf(fab(f)),pads
def valid(t):
 court,body,pads=t
 return not courts.intersects(court) and not bodyblocked.intersects(body) and not any(padblocked[n].intersects(g) for n,g in pads)
cap=[]
for angle in [0,90,180,270]:
 for x in np.arange(37.5,38.5001,.05):
  for y in np.arange(14.5,15.5001,.05):
   x,y=round(float(x),4),round(float(y),4);t=transformed('C1602',angle,x,y)
   if valid(t):cap.append({'position_mm':[x,y],'rotation_deg':angle,'geometry':t})
rows=[]
for angle in [0,90,180,270]:
 for x in np.arange(30,46.0001,.1):
  for y in np.arange(12,24.0001,.1):
   x,y=round(float(x),4),round(float(y),4);t=transformed('R1601',angle,x,y)
   if not valid(t):continue
   feasible=[i for i,q in enumerate(cap) if not t[0].intersects(q['geometry'][0])]
   if not feasible:continue
   rows.append({'position_mm':[x,y],'rotation_deg':angle,'distance_from_original_mm':Point(x,y).distance(Point(xy(fps['R1601'].GetPosition()))),'compatible_cap_indices':feasible})
rows.sort(key=lambda r:r['distance_from_original_mm'])
data={'scope':__doc__,'source_sha256':c.sha,'removed_track_uuids_for_screen':sorted(removed),'capacitor_placements':[{k:v for k,v in r.items() if k!='geometry'} for r in cap],'resistor_placements':rows,'routing_and_thermal_qualification':'NOT_TESTED'}
out.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({'cap_count':len(cap),'resistor_count':len(rows),'nearest_resistors':rows[:10]}),flush=True)
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest()==c.sha
