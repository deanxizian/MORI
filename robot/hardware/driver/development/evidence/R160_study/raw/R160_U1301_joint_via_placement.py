"""Read-only native U1301 placement comparison near its existing divider group.
Joint study treats C1303, R1303, R1307 and R1502 as separately movable; no positions for those parts are claimed or adopted. No board is saved. Nominal bodies/courtyards and exact native pad copper are
screened. All ground holes and PTHs remain fixed; non-ground via conflicts are explicitly listed as unbuilt relocation work. Reported copper conflicts are work still to reroute, not waived DRC.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R160-U1301-joint-via-placement.json';assert not out.exists()
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert c.sha=='bf719a717ffba2a1468126f6a71a1cc3703980fedf647caf8af07c1a9cef62a0'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[node],type_ignores=[]),'fab','exec'))
fps={f.GetReference():f for f in c.footprints};source=fps['U1301'];own={uid(p) for p in source.Pads()}
old_center=xy(source.GetPosition());old_angle=source.GetOrientationDegrees()
others=[(f.GetReference(),polyset(f.GetCourtyard(pcb.B_CrtYd))) for f in c.footprints if f.GetLayer()==pcb.B_Cu and f.GetReference() not in ['U1301','C1303','R1303','R1307','R1502']]
all_holes=unary_union([Point(xy(v.GetPosition())).buffer(v.GetDrillValue()/2e6) for v in c.vias if v.GetNetname()=='GND']+[Point(xy(p.GetPosition())).buffer(max(xy(p.GetDrillSize()))/2) for p in c.pads if max(xy(p.GetDrillSize()))>0])
rows=[];counts={'poses':0,'courtyard_reject':0,'body_hole_reject':0,'pad_clearance_reject':0}
for angle in [90,0,180,-90]:
 for ix in range(240,271):
  for iy in range(88,121):
   x,y=ix/4,iy/4;counts['poses']+=1
   f=pcb.FOOTPRINT(source);f.SetPosition(pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y)));f.SetOrientationDegrees(angle)
   courtyard=polyset(f.GetCourtyard(pcb.B_CrtYd));body=fab(f)
   hits=[ref for ref,shape_ in others if not courtyard.is_empty and courtyard.intersection(shape_).area>1e-6]
   if hits:counts['courtyard_reject']+=1;continue
   if body.intersects(all_holes):counts['body_hole_reject']+=1;continue
   pad_hits=[]
   for p in f.Pads():
    ps=shape(p,pcb.B_Cu)
    for q in c.pads:
     if uid(q) in own or q.GetParentFootprint().GetReference() in ['C1303','R1303','R1307','R1502'] or not q.IsOnLayer(pcb.B_Cu):continue
     other=c.shapes.get((uid(q),'B.Cu'))
     if other is not None and p.GetNetname()!=q.GetNetname() and ps.distance(other)<.199998:pad_hits.append(c.pad_name(q))
   if pad_hits:counts['pad_clearance_reject']+=1;continue
   pad_shapes=[(p.GetNetname(),shape(p,pcb.B_Cu)) for p in f.Pads()]
   conflicts=[]
   for t in c.tracks:
    ts=c.shapes.get((uid(t),'B.Cu'))
    if ts is None:continue
    under_body=ts.intersection(body).area>1e-6
    bad_pad=any(net!=t.GetNetname() and sh.distance(ts)<.199998 for net,sh in pad_shapes)
    if under_body or bad_pad:conflicts.append({'uuid':uid(t),'net':t.GetNetname(),'via':isinstance(t,pcb.PCB_VIA),'body':under_body,'pad_clearance':bad_pad})
   if any(r['via'] and r['net']=='GND' for r in conflicts):continue
   rows.append({'position_mm':[x,y],'rotation_deg':angle,'track_conflicts':conflicts,'count':len(conflicts),
    'old_to_new_mm':Point(old_center).distance(Point(x,y))})
rows.sort(key=lambda r:(r['count'],abs(r['position_mm'][0]-64.5)+abs(r['position_mm'][1]-24.5)))
out.write_text(json.dumps({'scope':__doc__,'source_sha256':c.sha,'counts':counts,'candidate_count':len(rows),'candidates':rows,'physical':'NOT_TESTED'},indent=2)+'\n')
print(json.dumps({'counts':counts,'candidate_count':len(rows),'best':rows[:12]}))
