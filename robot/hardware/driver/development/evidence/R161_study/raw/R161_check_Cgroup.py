"""Ten-part joint candidate with D1802/D1803 and wheel-power branch retained.
Geometry screening only. Old-copper conflicts remain explicit unfinished work.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161-Cgroup.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fs={f.GetReference():f for f in c.footprints}
poses={'U1301':([65.2,27.9],0),'C1301':([68.9,28.5],-90),'C1302':([68.8,24.25],90),'C1303':([68.8,27.9],-90),
 'R1307':([62.2,16.3],90),'R1502':([62.9,31.15],-90),'R1504':([59.5,32.75],-90),'C1501':([53.3,29.55],-90),
 'R1311':([42.9,23.5],90),'R1312':([43.35,26.9],90)}
placed={}
for ref,(pos,angle) in poses.items():
 f=pcb.FOOTPRINT(fs[ref]);f.SetPosition(pcb.VECTOR2I(*(round(x*1e6) for x in pos)));f.SetOrientationDegrees(angle);f.BuildCourtyardCaches();placed[ref]=f
fixed=[f for f in c.footprints if f.GetReference() not in placed];rows=[]
for ref,f in placed.items():
 ly=f.GetLayer();ln=c.board.GetLayerName(ly);cy=polyset(f.GetCourtyard(pcb.B_CrtYd if ly==pcb.B_Cu else pcb.F_CrtYd));body=fab(f)
 pads=[(p.GetNumber(),p.GetNetname(),shape(p,ly),xy(p.GetPosition())) for p in f.Pads()]
 hard=[]
 for q in fixed+list(placed.values()):
  if q.GetReference()==ref:continue
  if q.GetLayer()==ly:
   qc=polyset(q.GetCourtyard(pcb.B_CrtYd if ly==pcb.B_Cu else pcb.F_CrtYd))
   if cy.distance(qc)<.01:hard.append({'kind':'courtyard','other':q.GetReference(),'distance_mm':cy.distance(qc)})
  for p in q.Pads():
   if not p.IsOnLayer(ly):continue
   sh=shape(p,ly)
   if p.GetAttribute()==pcb.PAD_ATTRIB_PTH and cy.distance(sh)<.005:hard.append({'kind':'PTH_courtyard','other':c.pad_name(p)})
   for n,net,land,_ in pads:
    if net!=p.GetNetname() and land.distance(sh)<.202:hard.append({'kind':'foreign_pad','pad':n,'other':c.pad_name(p),'distance_mm':land.distance(sh)})
   drill=max(xy(p.GetDrillSize()))
   if drill:
    hole=Point(xy(p.GetPosition())).buffer(drill/2)
    if body.intersects(hole):hard.append({'kind':'body_hole','other':c.pad_name(p)})
    for n,_,land,_ in pads:
     if land.distance(hole)<.302:hard.append({'kind':'pad_hole','pad':n,'other':c.pad_name(p),'distance_mm':land.distance(hole)})
 for n,_,land,_ in pads:
  if not box(.505,.505,69.495,34.495).covers(land):hard.append({'kind':'pad_edge','pad':n})
 pending=[]
 for t in c.tracks:
  sh=c.shapes.get((uid(t),ln))
  if sh is None:continue
  via=isinstance(t,pcb.PCB_VIA);body_hit=body.intersection(sh).area>1e-6
  bad=[n for n,net,land,_ in pads if (net!=t.GetNetname() or via) and land.distance(sh)<.202]
  if via:
   hole=Point(xy(t.GetPosition())).buffer(t.GetDrillValue()/2e6)
   bad+=['hole:'+n for n,_,land,_ in pads if land.distance(hole)<.302]
  if body_hit or bad:
   row={'uuid':uid(t),'net':t.GetNetname(),'via':via,'body':body_hit,'pads':bad}
   if via and t.GetNetname()=='GND':hard.append({'kind':'fixed_GND_via',**row})
   else:pending.append(row)
 row={'reference':ref,'position_mm':list(xy(f.GetPosition())),'rotation_deg':f.GetOrientationDegrees(),'face':ln,
  'pads':[{'number':n,'net':net,'position_mm':list(pos)} for n,net,_,pos in pads],
  'hard_clashes':hard,'pending_copper_conflicts':pending}
 rows.append(row);print(json.dumps(row),flush=True)
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'placements':rows,'adopted':False},indent=2)+'\n')
