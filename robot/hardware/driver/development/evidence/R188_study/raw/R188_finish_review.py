"""Source-bound final reference, actual ground-fill and local layout review."""
import hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,data):
    with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
src=read(dev/'evidence/R187F/reference-survey.json');dst=read(b/'R188C-reference-survey.json')
a={r['uuid']:r for r in src['tracks']};d={r['uuid']:r for r in dst['tracks']}
af={u for u,r in a.items() if r['status']=='REVIEW_REQUIRED'};df={u for u,r in d.items() if r['status']=='REVIEW_REQUIRED'}
assert not df-af and (len(af),len(df))==(76,75)
assert not [u for u in a.keys()&d.keys() if d[u]['missing_reference_mm2']>a[u]['missing_reference_mm2']+1e-6]
assert af-df=={'46b45438-08f9-40a3-97c0-eeccfd4d2b5b'}
assert not any(r['status']=='REVIEW_REQUIRED' for r in d.values() if r['net']=='Net-(U1702-INA+)')
write(b/'R188C-reference-comparison.json',dict(source_sha256=src['source_sha256'],candidate_sha256=dst['source_sha256'],
    status='PASS',before_flagged_tracks=76,after_flagged_tracks=75,before_flagged_nets=37,after_flagged_nets=36,
    removed_flags=[a[u] for u in af-df],new_flags=[],worsened_retained_tracks=[],threshold_mm2=1e-6,physical='NOT_TESTED'))
previous=read(dev/'evidence/R187F/reference-review-queue.json');classes={r['net']:r['screening_classification'] for r in previous['items']}
items=[dict(r,status='REVIEW_REQUIRED',screening_classification=classes[r['net']],electrical_fault_confirmed=False,
    qualification='NOT_TESTED',track_uuids=sorted(u for u in df if d[u]['net']==r['net'])) for r in dst['by_net']]
write(b/'R188C-reference-review-queue.json',dict(scope=previous['scope'],source_sha256=dst['source_sha256'],source_tracks=1305,
    flagged_tracks=75,flagged_nets=36,items=items,source_saved=False,physical='NOT_TESTED',manufacturing_release=False))
source=Copper(dev/'native/MORI_Interface_C3.kicad_pcb');c=Copper(b/'R188C/MORI_Interface_C3.kicad_pcb')
assert source.sha==src['source_sha256'] and c.sha==dst['source_sha256']
grounds=[v for v in c.vias if v.GetNetname()=='GND'];assert len(grounds)==114
contacts=[dict(uuid=uid(v),position_mm=list(xy(v.GetPosition())),fill_contact_mm2=c.ground_reference_contacts(v)) for v in grounds]
assert all(all(area>1e-8 for area in r['fill_contact_mm2'].values()) for r in contacts)
write(b/'R188C-ground-contact-review.json',dict(status='PASS',source_sha256=source.sha,candidate_sha256=c.sha,
    original_ground_via_count=114,retained_identities=114,explicitly_moved=1,unchanged_positions=113,
    method='Positive-area native zone-fill contact; a via annulus is not used as its own plane evidence.',contacts=contacts,
    physical='NOT_TESTED',manufacturing_release=False))
g=read(b/'R188C-geometry-review.json');p=read(b/'R188C-planned-delta.json')
assert p['status']=='PASS' and len(p['checks'])==2524
return_path=p['ground_direct_return_review'][0]['direct_returns'][0]
assert return_path['planned_length_mm']<return_path['source_length_mm']
via=c.by_id['68fd19fb-550e-48aa-9664-2b3293e9421c']
clearance=[]
for u in ['91ef992b-7d59-4fdf-9c25-f80e62b58f1e','0d890a6c-c371-4632-8523-46e775782752']:
    other=c.by_id[u];gap=math.dist(xy(via.GetPosition()),xy(other.GetPosition()))-(via.GetWidth()+other.GetWidth())/2e6
    assert gap>.1999996
    clearance.append(dict(other_uuid=u,other_net=other.GetNetname(),nominal_circle_edge_gap_mm=gap))
unshielded=[r for r in g['foreign_copper_projections'] if r['unshielded_added_mm2']>1e-8]
assert len(unshielded)==1 and unshielded[0]['net']=='Net-(U1001-S2_{slash}_WHEEL_sense)' and unshielded[0]['other_net']=='MOTION_3V3'
assert not g['same_face_nominal_body_hits'] and all(r['unshielded_added_mm2']<1e-8 for r in g['body_projections'])
u1001=next(f for f in c.footprints if f.GetReference()=='U1001')
assert next(p.GetNetname() for p in u1001.Pads() if p.GetNumber()=='14')=='MOTION_3V3'
coupling=dict(source_sha256=source.sha,candidate_sha256=c.sha,local_development_layout_decision='PASS',
    new_unshielded_projection=unshielded[0],intervening_ground_between_In2_and_In3=False,
    native_stack_dielectrics_mm=dict(In3_to_In4_GND=.13,In3_to_In2_power=.9328),native_stack_is_not_supplier_verified=True,
    sampling_via_nearest_circle_clearances=clearance,direct_ground_return=return_path,
    disposition='Accept for continued development: the small added In3 sampling projection faces the same 3V3 supply used by U1001, with continuous nearer In4 ground and a shorter C1002 ground return. No new unshielded foreign signal/switching-node projection was found. This is a local design judgment, not a zero-noise or blanket power-plane exception.',
    geometry='New F comparator copper avoids mounted-face bodies. Its added opposite-face C1702 projection has intervening actual GND. The original In3 projection beneath D1801 contains no newly added copper. All 114 GND vias contact actual fill on both reference planes.',
    narrow_spacing='Nominal sampling-via circle gaps are only about 0.204 and 0.208 mm. They meet unchanged native rules; no extra fabrication tolerance or measured margin is inferred.',
    manufacturer_review=dict(url='https://www.ti.com/lit/ds/symlink/tps3700.pdf',document='TPS3700 SBVS187G, sections 8.3 and 10.1',
        observation='The manufacturer recommends local 0.1 uF VDD bypassing and attention to noisy monitored rails. C1702 remains the original 100 nF part with original supply and ground paths. Complete U1702 bypass/input/transient qualification remains open.'),
    full_noise_transient_thermal='NOT_TESTED',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False)
write(b/'R188C-coupling-review.json',coupling)
images=[dict(path=name+'/'+p.name,sha256=sha(p)) for name in ['R188-source-views','R188C-views'] for p in sorted((b/name).glob('*.png'))]
assert len(images)==10
write(b/'R188C-visual-review.json',dict(source_sha256=source.sha,board_sha256=c.sha,local_status='PASS',
    scope='Four source and all six final local copper-layer images actually viewed; native diagnostic projections, not GUI screenshots.',
    images_actually_viewed=images,observations=[
        'Comparator bridge keeps a long straight run at y12.65 with one deliberate entry offset beyond the U1302 CT antipad. The short final segment is inside R1704.2 copper; the branch to U1702 remains connected.',
        'C1002 ground escape uses the actual source x52.7 corridor. The explicit pad-centre-to-via path shortens from 4.043503 to 2.568503 mm at unchanged 0.20 mm width.',
        'Sampling via moves down-left while restoring its B and In3 tails. The B tail shortens, while the In3 tail adds a vertical end approach. No component or hole is added.',
        'F body avoidance, actual reference coverage and the separately recorded interlayer supply projection have been checked. No claim of complete analog accuracy, EMC or thermal validation follows.'
    ],coupling_review='coupling-review.json',whole_board_visual='NOT_TESTED',whole_board_route_style='NOT_TESTED',
    full_noise_transient_thermal='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False))
write(b/'R188-diagnostic-corrections.json',dict(
    A='A used a ground site crossing In2 U401-1Y and inadequate sampling-via clearances. All failures retained; no adoption.',
    B='B fixed via positions but guessed x52.6 for the ground escape; actual source is x52.7. Native C1002-pad spacing failed. C uses the actual source escape.',
    comparator_offset='A/B started the input downstep too early and lost reference above the U1302 CT via. C delays it until x51.35; native-reference threshold is unchanged.',
    return_lengths='The geometry sum of old GND tracks excludes the 0.35 mm in-pad centre-to-exit distance. Direct-return validation includes it: 4.043503 to 2.568503 mm. Do not compare the unadjusted track sum as the full return.',source_saved=False))
assert sha(Path(source.path))==source.sha and sha(Path(c.path))==c.sha
print(json.dumps(dict(local_review='PASS',ground_vias_contacting_both_planes=114,reference_flags='76 to 75',images_viewed=10,physical='NOT_TESTED')))
