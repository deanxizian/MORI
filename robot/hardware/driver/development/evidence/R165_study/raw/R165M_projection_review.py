"""Record actual local image review and bounded per-component projection findings."""
import collections,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');out=b/'R165M-visual-review.json';assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R165M/MORI_Interface_C3.kicad_pcb')
i=json.loads((b/'R165M-inspection.json').read_text());reg=json.loads((b/'R165M-verification/regression.json').read_text());assert not i['same_face_nominal_body_hits']
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in reg['new_copper_review'])
review={
'C1301':'F-side 100 pF UV input capacitor has one In3 divider-node projection. In1 separates the F component from the inner route; the route has continuous In4 reference. The actual input connection and nearby ground are preserved. Input pickup and parasitics remain unqualified.',
'C1303':'F divider-node trace projects under the B-side 100 nF U1301 decoupler. F uses In1 reference; the B decoupling supply/ground escapes remain explicit and pass critical adjacency. Capacitive pickup and local temperature have not been measured.',
'C1501':'UV and FAULT In3 routes pass below the B-side 100 pF OV filter. In4 is continuous between these routes and the filter. The B path U1501.4 to C1501.1 is retained while the OV transfer moves downstream to (55.9,33.9). Filter parasitics and fault transient coupling remain open engineering checks.',
'C1503':'The In3 UV output passes under the B-side 100 nF decoupler through continuous In4 reference. Its original supply and direct ground paths remain. No thermal or transient immunity qualification is inferred.',
'J401':'B ground escape and allowed In2 OV signal project under the unchanged F connector. Native pad/via/body restrictions and four-spoke ground thermals pass. In2 references In1; B references In4. Connector/cable transient coupling and loaded temperature remain unqualified.',
'J402':'B and In2 OV plus In3 UV/FAULT routes project under the unchanged F connector. All native restrictions remain and no F-face body route was introduced. In1/In4 reference screens pass; In2/In3 mutual crossings are separately enumerated. Installed connector thermal and cable EMC remain open.',
'J702':'The relocated B detector/divider network and allowed inner-layer signal/power paths project under the unchanged F camera connector. Same-face routes escape component pads without new Fab crossings; native J702 ground thermals pass. Inner/B references pass, but populated height, connector heat and camera supply/noise coupling are not qualified.',
'R1304':'F OV input trace projects under the B 90.9k divider resistor, with continuous In1 reference. B resistor identity and original connections stay unchanged. Pickup into high-impedance divider nodes requires the full circuit/EMC review; no thermal validation inferred.',
'R1501':'In3 UV output projects under the B 90.9k divider resistor; continuous In4 separates them. Nominal divider-node connections and critical adjacency pass. Analog pickup and temperature-induced threshold shift remain unqualified.',
'R1502':'Allowed In2 OV and In3 FAULT routes project under the B 54.9k divider resistor. The B node is separated by In4; In2/In3 routes use their own continuous reference planes. Adjacent-layer crossing geometry is recorded separately, without claiming a crosstalk/thermal pass.',
'R1503':'In2 HEAD_VM and In3 FAULT project under the B 24.3k resistor after the explicit F-to-B move. Native pad order, resistance, guards and reference coverage are checked. Supply/fault injection and local heating still need full engineering review.',
'R1504':'In3 UV output projects under the B 10k divider resistor. In4 remains continuous and the original divider connections are restored. No threshold-noise or thermal qualification is inferred.',
'R402':'F OV input route passes below the B 33R logic-series resistor. F/In1 reference is continuous and the original B logic path is preserved. Logic-edge injection into the detector input remains a full-board EMC review item.',
'R404':'F OV input route passes below the B 100k resistor through continuous In1 reference. Its original pads and wiring stay unchanged. High-impedance coupling and temperature behavior remain unqualified.',
'U1301':'F UV input and In3 divider-node paths project under the moved B TPS3700. In4 separates the B package from inner routes, and F has In1 reference. Actual UV/OV, VDD, GND, UV_N and FAULT pad connections are checked; full TI layout/noise/thermal qualification is still open.',
'U1501':'In3 UV output passes under the existing B TPS3700 body through continuous In4 reference. The OV input retains its B filter path and VDD retains both 3V3 transfers. Complete manufacturer layout, protection response and temperature qualification remain open.'}
groups=collections.defaultdict(list)
for row in i['opposite_or_internal_body_hits']:groups[row['component']].append(row)
assert set(groups)==set(review)
projections=[{'component':ref,'tracks':groups[ref],'reference_geometry':'PASS within recorded native screen','review':review[ref],'coupling_qualification':'NOT_TESTED','thermal_qualification':'NOT_TESTED','development_disposition':'Retained for continued independent development; not release qualification'} for ref in sorted(groups)]
# Enumerate actual new-to-existing adjacent inner-layer trace overlaps; no field-solver claims.
seen=set();crossings=[]
for t in c.segments:
 if uid(t) in a.by_id:continue
 ly=c.board.GetLayerName(t.GetLayer())
 if ly not in ('In2.Cu','In3.Cu'):continue
 other='In3.Cu' if ly=='In2.Cu' else 'In2.Cu'
 for u in c.segments:
  if c.board.GetLayerName(u.GetLayer())!=other or t.GetNetname()==u.GetNetname():continue
  key=tuple(sorted((uid(t),uid(u))))
  if key in seen:continue
  area=c.shapes[uid(t),ly].intersection(c.shapes[uid(u),other]).area
  if area<=1e-6:continue
  seen.add(key);crossings.append({'first_uuid':uid(t),'first_net':t.GetNetname(),'first_layer':ly,'second_uuid':uid(u),'second_net':u.GetNetname(),'second_layer':other,'nominal_projection_overlap_mm2':area})
views=sorted((b/'R165M-views').glob('*.png'));assert len(views)==12
rows={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'board_sha256':c.sha,'source_sha256':a.sha,
'local_status':'PASS','scope':'Actual review of all six candidate layers at x40..70/y14..35, three same-window R159H source views and three transfer-region details at x52.3..57.2/y29..34.6. Native polygon drawings, not GUI screenshots, full-board or physical qualification.',
'images_actually_viewed':[{'path':'images/'+p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'actually_viewed':True} for p in views],
'new_same_face_nominal_body_hits':0,'opposite_or_internal_projections':projections,
'adjacent_inner_trace_crossings':{'native_In2_In3_dielectric_stack_mm':[.1164,.7,.1164],'native_nominal_total_mm':.9328,'stackup_status':'Native design allocation only; manufacturer stackup not certified','crossings':crossings,'electromagnetic_simulation':'NOT_TESTED'},
'observations':[
'R1311/R1312 form the restored right-edge bias pair; their outward ENABLE escape and direct middle/ground paths are visible. Original ENABLE transfer and two In3 tracks are restored.',
'UV/OV divider rows are grouped around the relocated U1301; C1303 remains 100nF decoupling, while C1301/C1302/C1501 remain 100pF input-filter parts. No component value, schematic or pin map changed.',
'The UV transfer at (46.3,29.65) and Q1301 0.05mm downward move provide a B path clear of the transistor nominal body. R1031 retains its outward F lead and same filled F copper to both unchanged nearby GND vias.',
'The original OV transfer moves from (54.4,31.8) to (55.9,33.9), preserving U1501.4-to-C1501.1 on B. The new FAULT transfer is (54.3,33.9). This opens a referenced In3 channel between the two unchanged 3V3 transfers.',
'UV In3 route is 19.844077mm and restored FAULT In3 route 18.257926mm. FAULT has deliberate bends around the existing lower 3V3 reference void; its last 0.206155mm centreline lead lies inside the existing via land. The exposed direct-to-centre alternative L was rejected for reference loss.',
'The upper In3 0.48mm 3V3 corridor is preserved. The lower 3V3 transfer at (54.4,33.05) uses the existing continuous In2 supply; its local In3 island is not claimed as a continuous In3 supply path. All recorded 0.48mm terminal screens pass.'
],
'whole_board_visual':'NOT_TESTED','whole_board_route_style':'NOT_TESTED','manufacturer_layout_qualification':'NOT_TESTED','physical':'NOT_TESTED','manufacturing_release':False}
with out.open('x') as f:json.dump(rows,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'projection_rows':len(i['opposite_or_internal_body_hits']),'components':len(projections),'adjacent_inner_crossings':len(crossings),'maximum_overlap_mm2':max([x['nominal_projection_overlap_mm2'] for x in crossings],default=0),'images_viewed':len(views)}))
