"""Read-only compact Schottky/detector group check using source native geometry."""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R161-compact-group-v4.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fs={f.GetReference():f for f in c.footprints}
poses={'U1301':([67.8,23.4],90),'D1803':([64.4,21.3],90),
       'C1303':([68.6,19.8],90),'C1302':([67.0,19.8],90),'C1301':([68.9,28.5],-90),
       'R1311':([61.1,15.7],90),'R1312':([62.65,15.7],-90)}
placed={}
for ref,(pos,angle) in poses.items():
 f=pcb.FOOTPRINT(fs[ref]);f.SetPosition(pcb.VECTOR2I(*(round(x*1e6) for x in pos)));f.SetOrientationDegrees(angle);placed[ref]=f
fixed=[f for f in c.footprints if f.GetReference() not in poses]
rows=[]
for ref,f in placed.items():
 ly=f.GetLayer();ln=c.board.GetLayerName(ly);cy=polyset(f.GetCourtyard(pcb.B_CrtYd if ly==pcb.B_Cu else pcb.F_CrtYd));body=fab(f)
 pad_shapes=[(p.GetNumber(),p.GetNetname(),shape(p,ly),xy(p.GetPosition())) for p in f.Pads()]
 clashes=[]
 for q in fixed+list(placed.values()):
  if q.GetReference()==ref:continue
  if q.GetLayer()==ly:
   overlap=cy.intersection(polyset(q.GetCourtyard(pcb.B_CrtYd if ly==pcb.B_Cu else pcb.F_CrtYd))).area
   if overlap>1e-6:clashes.append({'kind':'courtyard','other':q.GetReference(),'area_mm2':overlap})
  for p in q.Pads():
   if not p.IsOnLayer(ly):continue
   sh=shape(p,ly)
   for number,net,land,_ in pad_shapes:
    if net!=p.GetNetname() and land.distance(sh)<.2005:clashes.append({'kind':'foreign_pad','pad':number,'other':c.pad_name(p),'distance_mm':land.distance(sh)})
   drill=max(xy(p.GetDrillSize()))
   if drill:
    hole=Point(xy(p.GetPosition())).buffer(drill/2)
    if body.intersects(hole):clashes.append({'kind':'body_hole','other':c.pad_name(p)})
    for number,_,land,_ in pad_shapes:
     if land.distance(hole)<.3005:clashes.append({'kind':'pad_hole','pad':number,'other':c.pad_name(p),'distance_mm':land.distance(hole)})
 for v in c.vias:
  if v.GetNetname()!='GND':continue
  sh=shape(v,ly);hole=Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6)
  if body.intersects(sh):clashes.append({'kind':'body_GND_via','uuid':uid(v)})
  for number,_,land,_ in pad_shapes:
   if land.distance(sh)<.2005 or land.distance(hole)<.3005:clashes.append({'kind':'pad_GND_via','pad':number,'uuid':uid(v),'position_mm':xy(v.GetPosition()),'distance_mm':land.distance(sh)})
 pending=[]
 for t in c.tracks:
  sh=c.shapes.get((uid(t),ln))
  if sh is None:continue
  via=isinstance(t,pcb.PCB_VIA)
  if body.intersection(sh).area>1e-6 or any((net!=t.GetNetname() or via) and land.distance(sh)<.2005 for _,net,land,_ in pad_shapes):
   pending.append({'uuid':uid(t),'net':t.GetNetname(),'via':via})
 row={'reference':ref,'position_mm':xy(f.GetPosition()),'rotation_deg':f.GetOrientationDegrees(),
  'footprint_id':f.GetFPIDAsString(),
  'pads':[{'number':n,'net':net,'position_mm':list(pos)} for n,net,_,pos in pad_shapes],
  'hard_clashes':clashes,'pending_copper_conflicts':pending}
 rows.append(row);print(json.dumps(row),flush=True)
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'placements':rows,'adopted':False},indent=2)+'\n')
