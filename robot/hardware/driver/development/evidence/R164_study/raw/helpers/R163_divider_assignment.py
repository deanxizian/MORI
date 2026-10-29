"""Read-only grouped resistor reassignment between existing physical slots.
Native copies preserve values, pad numbering and sizes. Two passive side
changes are proposals only. Fixed interfaces, all GND vias and native keepouts
remain source constraints; existing non-ground copper conflicts are reported.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R163-divider-assignment.json';assert not out.exists()
c=Copper(str(b/'R162D/MORI_Interface_C3.kicad_pcb'));fs={f.GetReference():f for f in c.footprints}
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
poses=[('R1501','B.Cu',[57.5,29.25],90),('R1502','B.Cu',[57.5,32.5],90),('R1503','B.Cu',[59.5,32.75],-90),
       ('R1504','B.Cu',[60.425,29.75],-90),('R1301','B.Cu',[62.5,33.5],180),('R1302','F.Cu',[68.9,28.5],90),
       ('R1303','B.Cu',[62.9,31.15],-90),('R716','B.Cu',[60.75,25.25],0)]
moving={r[0] for r in poses};fixed=[f for f in c.footprints if f.GetReference() not in moving]
proposed=[]
for ref,face,pos,angle in poses:
 f=pcb.FOOTPRINT(fs[ref]);lid=c.ids[face]
 if f.GetLayer()!=lid:f.Flip(f.GetPosition(),False)
 f.SetPosition(pcb.VECTOR2I(*(round(x*1e6) for x in pos)));f.SetOrientationDegrees(angle);f.BuildCourtyardCaches()
 assert f.GetLayer()==lid
 proposed.append(f)
for f in fixed:f.BuildCourtyardCaches()
rows=[]
for f in proposed:
 face=c.board.GetLayerName(f.GetLayer());layer=f.GetLayer();cy=polyset(f.GetCourtyard(pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd));body=fab(f);pads=list(f.Pads())
 conflicts=[]
 for g in fixed+[q for q in proposed if q!=f]:
  if g.GetLayer()==layer:
   gy=polyset(g.GetCourtyard(pcb.F_CrtYd if face=='F.Cu' else pcb.B_CrtYd))
   if cy.intersection(gy).area>1e-8:conflicts.append({'type':'courtyard','other':g.GetReference(),'area_mm2':cy.intersection(gy).area})
  for q in g.Pads():
   if not q.IsOnLayer(layer):continue
   sh=shape(q,layer)
   if q.GetAttribute()==pcb.PAD_ATTRIB_PTH and cy.intersects(sh):conflicts.append({'type':'PTH_in_courtyard','pad':c.pad_name(q)})
   for p in pads:
    if p.GetNetname()!=q.GetNetname() and shape(p,layer).distance(sh)<.2-1e-6:conflicts.append({'type':'pad_clearance','pad':p.GetNumber(),'other':g.GetReference()+'.'+q.GetNumber(),'gap_mm':shape(p,layer).distance(sh)})
 for v in c.vias:
  if v.GetNetname()!='GND':continue
  vs=shape(v,layer)
  if body.intersection(vs).area>1e-8:conflicts.append({'type':'source_GND_via_body','via':uid(v),'position_mm':xy(v.GetPosition())})
  for p in pads:
   if shape(p,layer).distance(vs)<.2-1e-6:conflicts.append({'type':'source_GND_via_pad','via':uid(v),'pad':p.GetNumber(),'position_mm':xy(v.GetPosition()),'gap_mm':shape(p,layer).distance(vs)})
 if not box(.505,.505,69.495,34.495).covers(unary_union([shape(p,layer) for p in pads])):conflicts.append({'type':'board_edge'})
 pending=[]
 for t in c.tracks:
  sh=c.shapes.get((uid(t),face))
  if sh is None or t.GetNetname()=='GND':continue
  via=isinstance(t,pcb.PCB_VIA)
  if body.intersection(sh).area>1e-8 or any((via or p.GetNetname()!=t.GetNetname()) and shape(p,layer).distance(sh)<.2-1e-6 for p in pads):
   pending.append({'uuid':uid(t),'net':t.GetNetname(),'via':via})
 rows.append({'reference':f.GetReference(),'value':f.GetValue(),'footprint':f.GetFPIDAsString(),'position_mm':xy(f.GetPosition()),'rotation_deg':f.GetOrientationDegrees(),'face':face,
  'source_face':c.board.GetLayerName(fs[f.GetReference()].GetLayer()),'pads':[{'number':p.GetNumber(),'net':p.GetNetname(),'position_mm':xy(p.GetPosition())} for p in pads],
  'placement_conflicts':conflicts,'pending_non_ground_copper':pending})
result={'scope':__doc__,'source_sha256':c.sha,'placements':rows,'placement_conflict_count':sum(len(r['placement_conflicts']) for r in rows),'adopted':False,'PCB_saved':False,'native_verification_required':True}
out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'placement_conflicts':result['placement_conflict_count'],'rows':[{'ref':r['reference'],'conflicts':r['placement_conflicts'],'pending_copper':len(r['pending_non_ground_copper'])} for r in rows]}))
