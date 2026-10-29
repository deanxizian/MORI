"""Native full passive-group comparison ordered around the actual INA300 pins.

Compare a vertical IN- resistor and horizontal IN+ resistor so LIMIT has a
separate left-side approach. Every newly conflicting old segment is listed
explicitly and remains a restoration obligation. Source GND vias stay fixed.
"""
import ast,json,sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from build_trial import move_body_guards,point_mm
b=Path('robot/.state/c3-completion/trials');p=json.loads((b/'R176D-plan.json').read_text())
p['revision']='R176F';p['scope']=__doc__
c=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');t=Copper(c.path)
poses={'R1701':([43.25,9.125],270),'R1706':([44.5,14.6],0),'R1707':([43.125,12.25],270)}
for spec in p['translations']:
 if spec['reference'] in poses:
  pos,angle=poses[spec['reference']];spec['delta_mm']=[round(pos[i]-spec['from_mm'][i],6) for i in range(2)];spec['rotation_deg']=angle
fps={f.GetReference():f for f in t.footprints}
for spec in p['translations']:
 f=fps[spec['reference']];old=xy(f.GetPosition());angle=f.GetOrientationDegrees();owned=[z for z in t.zones if z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_'+spec['reference']+'_')]
 reconstruct=spec.get('reconstruct_fixed_via_guards',False)
 move_body_guards(owned,spec['delta_mm'],reconstruct,spec['rotation_deg']-angle,old,spec.get('rotate_fixed_via_guards',False),spec.get('repartition_fixed_via_guards',False))
 f.SetOrientationDegrees(spec['rotation_deg']);f.Move(point_mm(spec['delta_mm']))
n=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab');exec(compile(ast.Module(body=[n],type_ignores=[]),'fab','exec'))
checks=[]
for tt in c.segments:
 u=uid(tt)
 if u in p['delete_copper']:continue
 ly=c.board.GetLayerName(tt.GetLayer());g=c.shapes[u,ly];reasons=[]
 for ref in poses:
  f=fps[ref]
  if t.board.GetLayerName(f.GetLayer())!=ly:continue
  if any(g.distance(shape(q,t.ids[ly]))<.1999996-1e-9 for q in f.Pads() if q.GetNetname()!=tt.GetNetname()):reasons.append('new_foreign_pad_'+ref)
  body=fab(f).difference(unary_union([shape(q,t.ids[ly]) for q in f.Pads()]))
  if g.intersection(body).area>1e-8:reasons.append('new_own_face_body_'+ref)
 if reasons:
  p['delete_copper'].append(u);p['deleted_copper_expected'][u]=dict(net=tt.GetNetname(),layer=ly,width_mm=tt.GetWidth()/1e6,start_mm=list(xy(tt.GetStart())),end_mm=list(xy(tt.GetEnd())))
  checks.append(dict(uuid=u,reasons=reasons,snapshot=p['deleted_copper_expected'][u]))
o=b/'R176F-plan.json';assert not o.exists();o.write_text(json.dumps(p,indent=2)+'\n')
(b/'R176F-preparation.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=c.sha,additional_retirements=checks,adopted=False),indent=2)+'\n')
print(json.dumps(dict(revision=p['revision'],additional_retirements=checks)))
