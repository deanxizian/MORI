"""Read current native continuity and local geometry; no engineering qualification."""
import json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R165M-metrics.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R165M/MORI_Interface_C3.kicad_pcb')
ag=a.pad_groups();cg=c.pad_groups();fs={f.GetReference():f for f in c.footprints}
pad=next(p for p in fs['R1031'].Pads() if p.GetNumber()=='2');land=c.shapes[uid(pad),'F.Cu']
parts_at_pad=[g for g in parts(c.copper['GND','F.Cu']) if g.intersects(land)]
ground_rows=[{'via_mm':pt,'same_F_copper_with_R1031_2':any(g.intersects(Point(pt).buffer(.2)) for g in parts_at_pad)} for pt in [[45.65,30],[47,30]]]
s=json.loads((b/'R165K-power-spine.json').read_text());spine=LineString(s['points_mm']).buffer(.24)
retained_power=spine.difference(c.copper['MOTION_3V3','In3.Cu']).area
pairs=c.connected_pairs('MOTION_3V3',.48);power_vias={xy(v.GetPosition()):uid(v) for v in c.vias if v.GetNetname()=='MOTION_3V3'}
power_rows=[]
for pt in [(52.8,21),(52.8,24.05),(50.15,17.8),(46.9,18),(54.4,33.05)]:power_rows.append({'from_via_mm':pt,'to_via_mm':[54.4,31],'all_layer_0_48_mm_screen':tuple(sorted((power_vias[pt],power_vias[(54.4,31)]))) in pairs})
# The lower power via remains connected to the main In2 fill at the original width.
g=c.copper['MOTION_3V3','In2.Cu'].buffer(-.24)
via1=c.by_id[power_vias[54.4,31]];via2=c.by_id[power_vias[54.4,33.05]]
in2_pair=any(r.intersects(c.shapes[uid(via1),'In2.Cu']) and r.intersects(c.shapes[uid(via2),'In2.Cu']) for r in parts(g))
last=LineString([[54.1,33.95],[54.3,33.9]])
v=next(v for v in c.vias if v.GetNetname()=='/FAULT_N' and xy(v.GetPosition())==(54.3,33.9))
rows={'source_sha256':a.sha,'board_sha256':c.sha,'counts':{'segments':len(c.segments),'vias':len(c.vias),'footprints':len(c.footprints),'new_segments':sum(uid(t) not in a.by_id for t in c.segments)},'group_count_changes':[{'net':n,'before':len(ag[n]),'after':len(cg[n]),'after_groups':cg[n]} for n in cg if len(cg[n])!=len(ag[n])], 'R1031_ground':{'value':fs['R1031'].GetValue(),'rows':ground_rows},'preserved_In3_0_48_spine_uncovered_mm2':retained_power,'power_via_rows':power_rows,'lower_power_via_In2_0_48_pair':in2_pair,'FAULT_last_lead':{'centreline_length_mm':last.length,'centreline_inside_existing_via_land':c.shapes[uid(v),'In3.Cu'].covers(last)},'relevant_component_values':{n:fs[n].GetValue() for n in ['C1301','C1302','C1303','C1501','C1503','R1304','R1501','R1502','R1503','R1504','R402','R404','U1301','U1501']},'physical':'NOT_TESTED','manufacturing_release':False}
assert retained_power<1e-6 and all(x['all_layer_0_48_mm_screen'] for x in power_rows) and in2_pair
assert all(x['same_F_copper_with_R1031_2'] for x in ground_rows)
assert rows['FAULT_last_lead']['centreline_inside_existing_via_land']
with out.open('x') as f:json.dump(rows,f,indent=2);f.write('\n')
print(json.dumps(rows,ensure_ascii=False))
