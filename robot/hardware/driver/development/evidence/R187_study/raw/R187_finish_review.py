"""Record completed local visual and coupling review without changing PCB bytes."""
import hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
b=Path('robot/.state/c3-completion/trials')
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(path,data):
    with path.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
src=read(b/'R187-source-reference-survey.json')
dst=read(b/'R187F-reference-survey.json')
a={r['uuid']:r for r in src['tracks']};c={r['uuid']:r for r in dst['tracks']}
oldflags={u for u,r in a.items() if r['status']=='REVIEW_REQUIRED'}
newflags={u for u,r in c.items() if r['status']=='REVIEW_REQUIRED'}
worsened=[u for u in a.keys()&c.keys() if c[u]['missing_reference_mm2']>a[u]['missing_reference_mm2']+1e-6]
assert not worsened and not newflags-oldflags
assert (len(oldflags),len(newflags))==(81,76)
assert not any(r['status']=='REVIEW_REQUIRED' for r in c.values() if r['net'].endswith('IMU_SCL'))
write(b/'R187F-reference-comparison.json',dict(source_sha256=src['source_sha256'],candidate_sha256=dst['source_sha256'],
    status='PASS',before_flagged_tracks=81,after_flagged_tracks=76,before_flagged_nets=38,after_flagged_nets=37,
    removed_flags=[a[u] for u in sorted(oldflags-newflags)],new_flags=[],worsened_retained_tracks=[],
    current_queue_required=True,threshold_mm2=1e-6,physical='NOT_TESTED'))
previous=read(Path('robot/hardware/driver/development/evidence/R186_study/raw/R186-reference-review-queue.json'))
categories={x['net']:x['screening_classification'] for x in previous['items']}
items=[]
for row in dst['by_net']:
    row=dict(row,status='REVIEW_REQUIRED',screening_classification=categories[row['net']],
             electrical_fault_confirmed=False,qualification='NOT_TESTED',
             track_uuids=sorted(u for u in newflags if c[u]['net']==row['net']))
    items.append(row)
write(b/'R187F-reference-review-queue.json',dict(scope=previous['scope'],source_sha256=dst['source_sha256'],
    source_tracks=dst['non_GND_tracks_reviewed'],flagged_tracks=76,flagged_nets=37,items=items,
    source_saved=False,physical='NOT_TESTED',manufacturing_release=False))
board=b/'R187F/MORI_Interface_C3.kicad_pcb';copper=Copper(board)
assert copper.sha==dst['source_sha256']
text=board.read_text()
def dielectric(n):
    chunk=re.search(r'\(layer "dielectric '+str(n)+r'"(.*?)\n\t\t\t\)',text,re.S).group(1)
    return [float(x) for x in re.findall(r'\(thickness ([0-9.]+)\)',chunk)]
assert dielectric(2)==[.13] and dielectric(3)==[.1164,.7,.1164]
parts_by_ref={f.GetReference():f for f in copper.footprints}
u402={p.GetNumber():p.GetNetname() for p in parts_by_ref['U402'].Pads()}
assert u402['14']=='MOTION_3V3' and u402['2']=='/01 {slash} Core/WHEEL_TX'
g=read(b/'R187F-geometry-review.json')
overlaps=[r for r in g['foreign_copper_projections'] if r['unshielded_added_mm2']>1e-8]
assert len(overlaps)==1
row=overlaps[0]
assert (row['net'],row['layer'],row['other_net'],row['other_layer'])==('/01 {slash} Core/WHEEL_TX','In2.Cu','MOTION_3V3','In3.Cu')
assert not g['same_face_nominal_body_hits']
assert all(r['unshielded_added_mm2']<1e-8 for r in g['body_projections'])
assert len(g['moved_transfer_review'])==2 and all(r['nearest_actual_ground_anchor_mm']<2 for r in g['moved_transfer_review'])
coupling=dict(source_sha256=src['source_sha256'],candidate_sha256=copper.sha,
    local_development_layout_decision='PASS',not_a_manufacturing_or_EMC_qualification=True,
    new_unshielded_projection=row,intervening_ground_between_In2_and_In3=False,
    native_stack_dielectrics_mm=dict(In2_to_In1_GND=.13,In2_to_In3_power=sum(dielectric(3))),
    native_stack_is_not_supplier_verified=True,U402_input_pin='2',U402_supply_pin='14',U402_supply_net=u402['14'],
    disposition='Accept this local layout change for continued development. The added projection is over the receiver supply plane, with continuous nearer In1 GND under the changed In2 route. No new unshielded signal, switching-node or high-energy copper projection was found. This is a design judgment, not a zero-coupling claim or a blanket power-plane exception.',
    body_and_thermal='No footprint or power-device position changes and no new holes. Same-face body hits are absent. Added WHEEL_TX projection under B-face R1001 has actual intervening In4 GND. 0.50/0.20 mm supply widths and total changed-feed length are preserved; all 50 source power checks pass. Complete heat and current-capacity qualification remains open.',
    reference='TI SCAA082A, sections 1.6 and 2.2: preserve nearby continuous reference and consider functional-block coupling; these general guidelines do not qualify this board.',
    reference_url='https://www.ti.com/lit/an/scaa082a/scaa082a.pdf',
    full_noise_transient_thermal='NOT_TESTED',whole_board_visual='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False)
write(b/'R187F-coupling-review.json',coupling)
images=[]
for name in ['R187-IMU-source','R187F-views']:
    for p in sorted((b/name).glob('*.png')):images.append(dict(path=name+'/'+p.name,sha256=sha(p)))
assert len(images)==10
write(b/'R187F-visual-review.json',dict(source_sha256=src['source_sha256'],board_sha256=copper.sha,
    local_status='PASS',scope='Four source layer images and six final native local layer images actually viewed; diagnostic native geometry, not KiCad GUI screenshots.',
    images_actually_viewed=images,
    observations=[
      'F clock leaves the existing left transfer and follows the open corridor below the unchanged J701 guards. Final clockwise bend approaches the right existing transfer from below, avoiding the remaining reference bite without moving the 3V3 via farther upward.',
      'The 0.20 mm final clock segment and 0.10 mm WHEEL_TX centering segment are inside their existing via lands; they are not exposed tiny zigzags.',
      'In2 WHEEL_TX makes one deliberate lower bypass around the relocated sampling transfer. Its short added span has full mapped In1 reference. The original In3 sampling connection is restored with a shorter local lead.',
      'B R1001 escape remains outward. The changed 3V3 feed retains 0.50 mm trunk and 0.20 mm bypass widths and unchanged combined centerline length.',
      'The two reference planes have the expected via antipads; the complete per-track audit closes all four IMU clock coverage flags and one WHEEL_TX In2 flag without changing exclusions or the 1e-6 mm2 threshold.',
      'The new In2/In3 supply projection has no intervening GND and is explicitly reviewed in coupling-review.json. It is not described as shielded.'
    ],coupling_review='coupling-review.json',whole_board_visual='NOT_TESTED',whole_board_route_style='NOT_TESTED',
    full_noise_transient_thermal='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False))
write(b/'R187-diagnostic-corrections.json',dict(
    D_and_E='Moving the 3V3 via farther upward introduced B supply reference deficits. D full native checks still have 19 opens/0 other DRC, but the custom reference requirement fails. Neither is adopted.',
    E_metadata='The E scope string inherited D wording; E description and actual plan place the via at y7.35, only 0.05 mm above C. Preserve original plan and build evidence.',
    nominal_pad_face='PAD.GetLayer is not the authoritative side for all native pads; footprint side/pad_faces are used. R1001 is B, not F.',
    helper_lookup='An rg lookup included nonexistent native_audit.py; no such module was read or used.',
    source_saved=False))
assert sha(board)==copper.sha
print(json.dumps(dict(local_review='PASS',reference_flags='81 to 76',images_viewed=10,physical='NOT_TESTED')))
