"""Exact-geometry and native roundtrip checks for vacated guard partitions.

No accepted board is written. Repartition keeps every source zone identity and
restriction and exactly the moved body minus original fixed via windows.
"""
import ast,json,sys,hashlib
from pathlib import Path
from shapely.affinity import rotate,translate
from shapely.geometry import box
from shapely.ops import unary_union
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from zone_expansion import zone_settings
from build_trial import repartition_via_guards,move_body_guards,point_mm
b=Path('robot/.state/c3-completion/trials');out=b/'R176-guard-checks';out.mkdir(exist_ok=False)
source=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
original_hash=hashlib.sha256(source.read_bytes()).hexdigest();assert original_hash=='7acdf187325f5eb86d44205b3276f316e08cfdc69ed5ff9e84308f0128fe155e'
oldfile=Path('robot/hardware/driver/development/evidence/R175_study/raw/helpers/build_trial.py')
node=next(n for n in ast.parse(oldfile.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='repartition_via_guards')
ns=dict(parts=parts,unary_union=unary_union);exec(compile(ast.Module(body=[node],type_ignores=[]),'frozen_R175_repartition','exec'),ns)
old=ns['repartition_via_guards'];rows=[]
def record(name,ok,**details):
 assert ok,(name,details);rows.append(dict(name=name,status='PASS',**details))
def rejected(name,regions,target):
 try:repartition_via_guards(regions,target)
 except ValueError as e:record(name,True,message=str(e));return
 raise AssertionError(name+' unexpectedly accepted')
for name,regions,target in [
 ('empty_partition_reused',{'a':box(0,0,2,2),'b':GeometryCollection()},box(0,0,2,2)),
 ('multiple_empty_partitions_reused',{'a':box(0,0,2,2),'b':GeometryCollection(),'c':GeometryCollection()},box(0,0,2,2)),
 ('empty_partition_for_disconnected_target',{'a':box(0,0,1,1),'b':GeometryCollection()},unary_union([box(0,0,1,1),box(2,0,3,1)])),
 ('nonempty_legacy_case',{'a':box(0,0,1,2),'b':box(1,0,2,2)},box(0,0,2,2))]:
 r=repartition_via_guards(regions,target)
 record(name,set(r)==set(regions) and all(len(parts(x))==1 and x.area>0 for x in r.values()) and unary_union(list(r.values())).symmetric_difference(target).area<1e-8)
 if name=='nonempty_legacy_case':
  expected=old(regions,target);record('synthetic_legacy_shapes_identical',all(r[k].equals_exact(expected[k],1e-9) for k in r))
rejected('empty_target_refused',{'a':GeometryCollection()},GeometryCollection())
rejected('too_few_UUIDs_for_disconnected_target_refused',{'a':box(0,0,1,1)},unary_union([box(0,0,1,1),box(2,0,3,1)]))
rejected('geometry_outside_target_refused',{'a':box(0,0,2,2)},box(0,0,1,1))
for name,ref,delta,angle in [
 ('R176_INA_small_translation','U1701',[0,.15],0),
 ('R176_supervisor_small_translation','U1302',[0,.15],0),
 ('R174_INA_270_replay','U1701',[1.5,0],270),
 ('R174_supervisor_replay','U1302',[-4.25,-2.1],0)]:
 c=Copper(str(source));f=next(f for f in c.footprints if f.GetReference()==ref)
 origin=xy(f.GetPosition());owned=[z for z in c.zones if z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_'+ref+'_')]
 vias=[z for z in owned if z.GetDoNotAllowVias()]
 before={uid(z):zone_settings(c.board,z) for z in owned}
 body=unary_union([polyset(z.Outline()) for z in owned if z.GetDoNotAllowTracks()])
 fixed=body.difference(unary_union([polyset(z.Outline()) for z in vias]))
 tr=lambda g:translate(rotate(g,-angle,origin=origin),xoff=delta[0],yoff=delta[1])
 target=tr(body).difference(fixed)
 transformed={uid(z):tr(polyset(z.Outline())).difference(fixed) for z in vias}
 vacated=[u for u,g in transformed.items() if g.is_empty]
 expected=repartition_via_guards(transformed,target)
 if vacated:
  try:old(transformed,target)
  except ValueError:record(name+'_frozen_code_reproduces_rejection',True,vacated_UUIDs=vacated)
  else:raise AssertionError('Expected original helper failure')
 else:
  legacy=old(transformed,target)
  record(name+'_legacy_geometry_identical',all(expected[u].equals_exact(legacy[u],1e-9) for u in expected))
 move_body_guards(owned,delta,True,angle,origin,True,True)
 f.SetOrientationDegrees(f.GetOrientationDegrees()+angle);f.Move(point_mm(delta))
 path=out/(name+'.kicad_pcb');pcb.SaveBoard(str(path),c.board);d=Copper(str(path))
 native={uid(z):z for z in d.zones if uid(z) in before}
 actual=unary_union([polyset(native[uid(z)].Outline()) for z in vias])
 record(name+'_native_roundtrip',set(native)==set(before) and all(zone_settings(d.board,native[u])==s for u,s in before.items()) and actual.symmetric_difference(target).area<1e-7 and actual.intersection(fixed).area<1e-7 and all(len(parts(polyset(z.Outline())))==1 for z in native.values()),
        zone_count=len(native),via_guard_count=len(vias),vacated_partitions=len(vacated),target_difference_mm2=actual.symmetric_difference(target).area)
# Differing restriction flags cannot be hidden by the new repartition path.
c=Copper(str(source));owned=[z for z in c.zones if z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_U1701_')]
v=next(z for z in owned if z.GetDoNotAllowVias());v.SetDoNotAllowTracks(True)
try:move_body_guards(owned,[0,.15],True,0,[47.25,12.35],True,True)
except ValueError as e:record('altered_native_restrictions_refused',True,message=str(e))
else:raise AssertionError('Mismatched source restrictions accepted')
record('accepted_source_bytes_unchanged',hashlib.sha256(source.read_bytes()).hexdigest()==original_hash)
(out/'result.json').write_text(json.dumps(dict(scope=__doc__,source_sha256=original_hash,status='PASS',checks=rows,native_rules_changed=False,adopted=False),indent=2)+'\n')
print(json.dumps(dict(status='PASS',checks=len(rows),native_roundtrips=4,source_unchanged=True)))
