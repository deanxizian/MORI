"""Record actual local visual review and exact native geometry metrics for G."""
import collections,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
a=Copper(str(dev/'native/MORI_Interface_C3.kicad_pcb'));c=Copper(str(b/'R168G/MORI_Interface_C3.kicad_pcb'))
p=json.loads((b/'R168G-plan.json').read_text());i=json.loads((b/'R168G-inspection.json').read_text());reg=json.loads((b/'R168G-final-checks/regression.json').read_text())
assert p['board_sha256']==a.sha and c.sha==reg['board_sha256'] and not i['same_face_nominal_body_hits']
def write(path,d):
 with path.open('x') as f:json.dump(d,f,indent=2,ensure_ascii=False);f.write('\n')
ga=a.pad_groups();gc=c.pad_groups();changes=[dict(net=n,before=len(ga[n]),after=len(gc[n]),after_groups=gc[n]) for n in ga if len(ga[n])!=len(gc[n])]
spine=json.loads((b/'R166-power-spine.json').read_text());assert spine['source_sha256']==a.sha
loss=LineString(spine['points_mm']).buffer(.24).difference(c.copper['MOTION_3V3','In2.Cu']).area
crossings=[]
new=[t for t in c.segments if uid(t) not in a.by_id]
for t in new:
 if c.board.GetLayerName(t.GetLayer())!='In2.Cu':continue
 line=LineString([xy(t.GetStart()),xy(t.GetEnd())])
 for q in c.segments:
  if c.board.GetLayerName(q.GetLayer())!='In3.Cu' or q.GetNetname()==t.GetNetname():continue
  other=LineString([xy(q.GetStart()),xy(q.GetEnd())]);hit=line.intersection(other)
  if hit.is_empty:continue
  va=[y-x for x,y in zip(xy(t.GetStart()),xy(t.GetEnd()))];vb=[y-x for x,y in zip(xy(q.GetStart()),xy(q.GetEnd()))]
  co=abs(sum(x*y for x,y in zip(va,vb))/(math.hypot(*va)*math.hypot(*vb)))
  crossings.append(dict(new_uuid=uid(t),other_uuid=uid(q),other_net=q.GetNetname(),angle_deg=math.degrees(math.acos(min(1,co))),intersection=hit.wkt))
metrics=dict(source_sha256=a.sha,board_sha256=c.sha,counts=dict(segments=len(c.segments),vias=len(c.vias),footprints=len(c.footprints),new_segments=len(new)),group_count_changes=changes,source_In2_0_48_spine_uncovered_mm2=loss,FAULT_trunk_length_mm=sum(math.dist(x,y) for x,y in zip(p['routes'][-1]['points_mm'],p['routes'][-1]['points_mm'][1:])),In2_In3_centerline_crossings=crossings,scope='Nominal native geometry only; not coupling, thermal, tolerance or physical qualification.')
write(b/'R168G-metrics.json',metrics)
notes={
 'U1702':'B ACT and FAULT escapes plus In2 FAULT lie beneath the F comparator. Their In4/In1 reference coverage passes; actual comparator input noise, output feedback, bypass-loop impedance and thermal drift remain unqualified.',
 'R402':'The F INA+ escape projects under the B wheel-bus series resistor. Continuous In1 ground is verified; wheel-bus edge coupling into the comparator input still needs full-board review and measurement.',
 'C1702':'F INA+ overlaps the B bypass capacitor projection. Reference coverage passes; this is not a qualification of VDD decoupling loop, capacitor parasitics or input error.',
 'Q1701':'The F 3V3 feed passes under the B fault transistor projection with continuous In1 ground. Switching interaction and thermal influence are not inferred from this geometry.',
 'J401':'In2 FAULT crosses the F wheel connector body projection with continuous In1 ground and original plated pins/guards retained. Harness return, load transients and coupling remain open.',
 'C1301':'In2 FAULT has short projection overlaps with the F UV input capacitor. Reference coverage passes; protection-edge injection into the analog input remains unqualified.',
 'U1301':'In2 FAULT approaches the original U1301 FAULT transfer under the B comparator projection. Native pin net/spacing and reference checks pass; protection dynamics and coupling remain open.',
 'D1803':'In2 FAULT passes under the B clamp body projection. Original clamp geometry is preserved and reference coverage passes; clamp pulse/thermal effects on the signal are NOT_TESTED.',
 'R1307':'In2 FAULT overlaps the B OV divider resistor projection. Ground coverage passes but analog divider noise and thermal drift require later full review.',
 'D1801':'B HEAD_UV_ENABLE crosses the F clamp projection; native keepouts and In4 reference pass. Clamp pulse coupling and thermal influence remain unqualified.'}
groups=collections.defaultdict(list)
for r in i['opposite_or_internal_body_hits']:groups[r['component']].append(r)
assert set(groups)==set(notes)
images=sorted((b/'R168G-views').glob('*.png'));assert len(images)==12
visual=dict(scope='Twelve actual native-geometry local views, two regions on six copper layers; top projection, not photos or whole-board acceptance.',source_sha256=a.sha,board_sha256=c.sha,images_actually_viewed=[dict(path='images/'+q.name,sha256=hashlib.sha256(q.read_bytes()).hexdigest()) for q in images],findings=[
 'The F comparator has an explicit outward ground path to the unchanged (57.475,18.2) source ground via. Both ground pads belong to the same 155-pad ground group.',
 'The F INA+ lead passes between ACT and wheel-transfer reference holes and approaches its pad outside the nominal body. This removes the D/F mounted-face intersections and reference gaps without weakening the full-stroke test.',
 'The B ACT output branches connect the relocated left/right original transfers outside Q1701. C1702 keeps a short supply lead to the unchanged right 3V3 transfer; full manufacturer bypass-loop qualification remains open.',
 'The In2 FAULT route bends around ACT/wheel holes and continues to the existing (67.45,28.35) transfer. The short final vertical join is inside its existing land. The original 0.48 mm upper 3V3 corridor and all 50 width checks are retained.',
 'The In1/In4 views and numerical checks establish no new or retained reference loss; they do not establish crosstalk, EMC, pulse response or physical qualification.'
 ],opposite_or_internal_projections=[dict(reference=r,entries=groups[r],review=notes[r],reference_screen='PASS',coupling_qualification='NOT_TESTED',thermal_qualification='NOT_TESTED') for r in sorted(groups)],In2_In3_crossings=crossings,new_same_face_nominal_body_hits=0,local_status='PASS',local_status_scope='Mounted-face geometry, native rules, source power/connectivity and reference screens only.',whole_board_visual='NOT_TESTED',whole_board_route_style='NOT_TESTED',manufacturer_thermal_coupling='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False)
write(b/'R168G-visual-review.json',visual)
print(json.dumps(dict(counts=metrics['counts'],group_changes=changes,spine_loss=loss,trunk_length=metrics['FAULT_trunk_length_mm'],crossings=crossings)))
