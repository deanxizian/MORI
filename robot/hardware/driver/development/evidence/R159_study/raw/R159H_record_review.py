"""Record the nine H/source native polygon images actually viewed by the reviewer."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
b=Path('robot/.state/c3-completion/trials');read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
i=read(b/'R159H-inspection.json');r=read(b/'R159H-verified/regression.json');p=read(b/'R159H-verified/planned-delta.json')
assert i['same_face_nominal_body_hit_count']==0 and i['required_new_supply_corridors_pass'] and i['source_local_pair_widths_preserved']
assert p['status']=='PASS' and len(p['checks'])==2573
assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']<=1e-6 for x in r['new_copper_review'])
notes={
 'R1703':'B-side RLIMIT/LATCH ground branches project below the F-side 100k divider resistor. The branches carry the local control return, not a newly assigned actuator load. In4 reference is continuous; F-side sensing retains In1 reference. Ground-to-input parasitic capacitance, noise and resistor temperature error are not quantified.',
 'R1702':'The B-side 0.35 mm UPS sampling branch projects below the F-side divider input resistor. It is the existing R1001 high-impedance battery sample, not a main motor feed. In4 and In1 ground references remain continuous. Supply-transient coupling and divider error require full-board/physical review.',
 'J701':'The B-side UPS sample and C505 3V3 feed project under the fixed F-side connector body. Native connector pads, clearance, body guards and fixed geometry remain unchanged. Both B routes have continuous In4 reference. Connector transient/ESD coupling and installed thermal clearance are not qualified.',
 'U1701':'F-side wheel sense, INA+ divider output and local 3V3 transfer project behind the B-side INA300. F traces have continuous In1 ground; local B return/reference is retained. No main actuator feed is moved below the IC. The new LIMIT trace stays outside its own B-side nominal body. Analog parasitics and thermal drift remain unqualified.',
 'R1701':'The F-side wheel sense branch projects behind the B-side RLIMIT resistor. This is a high-impedance sample, with continuous In1 reference and a separate explicit B-side RLIMIT return. Noise injection and temperature-dependent limit accuracy require later qualification.',
 'Q1601':'B-side wheel sense/LIMIT and In3 S2 sample traces project behind the unchanged F-side power MOSFET. They retain continuous In4 ground reference and all native copper/thermal/guard constraints. These are sensing/control traces rather than a new power loop. MOSFET transient coupling and heat-induced threshold error remain NOT_TESTED.'}
groups={}
for t in i['new_tracks']:
 for hit in t['nominal_body_projections']:
  assert not hit['same_face']
  groups.setdefault(hit['reference'],[]).append({'track_uuid':t['uuid'],'net':t['net'],'layer':t['layer'],'nominal_overlap_mm2':hit['area_mm2']})
assert set(groups)==set(notes)
images=[]
for name in ['candidate-H-F','candidate-H-In1','candidate-H-In2','candidate-H-In3','candidate-H-In4','candidate-H-B','source-F','source-B','source-In2']:
 f=b/'R159H-views'/(name+'.png');images.append({'path':'images/'+f.name,'sha256':sha(f),'actually_viewed':True})
d={'recorded_at_utc':datetime.now(timezone.utc).isoformat(),'board_sha256':i['candidate_sha256'],'source_sha256':i['source_sha256'],
 'local_status':'PASS','scope':'Local native polygon review at x=36..55 mm, y=4..18 mm, on all six candidate layers and F/B/In2 source views. Not a whole-board or physical review.',
 'images_actually_viewed':images,'new_same_face_nominal_body_hits':0,
 'observations':['R1702/R1703 escape outward; their intermediate connection is one 1.475 mm vertical segment. Nominal courtyard gap is 0.025 mm, not a measured assembly margin.',
 'R1002.1 now joins the retained R1707.1 wheel sample branch; all WHEEL_VM pads are in one connected group.',
 'C505 moves above the group and retains explicit supply and ground connections. INA300 C1701 decoupling is unchanged.',
 'The new UPS sampling hole (51.35,6.2) and 3.42 mm2 allocation extension stay outside the existing CAM 5 V corridor. The northward copper neck connects around the fixed ground hole.',
 'H preserves the fixed S2 hole and local 0.15 mm step. It also moves the retained UPS transfer to (45.29,10.05), jointly eliminating F nominal-body contact and G reference loss without a new ground hole or rule waiver.'],
 'opposite_or_internal_projections':[{'reference':ref,'tracks':groups[ref],'reference_continuity':'PASS within recorded native geometry screen','review':notes[ref],'coupling_qualification':'NOT_TESTED','thermal_qualification':'NOT_TESTED','development_disposition':'Retained for continued development with these limits'} for ref in sorted(groups)],
 'ina300_return_review':{'necessary_explicit_path_screen':'PASS','same_mounted_face_path':'R1701.1 -> (50.5,9.7) -> (50.5,10.87) -> retained B track -> (50.5,12.35) -> U1701.8',
 'nominal_track_centerline_length_mm':6.1,'layer_transition_required':False,'bypass_C1701_to_GND8_unchanged':True,
 'ground_plane_contacts':'The explicit B path also contacts existing ground fill and ground vias; it is not an isolated Kelvin ground and no such claim is made.',
 'scope':'The missing explicit return has been corrected. This does not qualify the full manufacturer layout, capacitance, loop behavior, coupling or thermal performance.',
 'manufacturer_layout_qualification':'NOT_TESTED'},
 'whole_board_visual':'NOT_TESTED','whole_board_route_style':'NOT_TESTED','historical_transition_flags':6,'physical':'NOT_TESTED','manufacturing_release':False}
with (b/'R159H-visual-review.json').open('x') as f:json.dump(d,f,indent=2);f.write('\n')
print(json.dumps({'local_status':d['local_status'],'images_actually_viewed':len(images),'projection_reference_groups':len(groups),'same_face_hits':0,'full_qualification':'NOT_TESTED'}))
