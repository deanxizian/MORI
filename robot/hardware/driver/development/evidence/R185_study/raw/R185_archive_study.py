"""Archive ground/transfer studies and tool validation; adopt no PCB candidate."""
import collections,gzip,hashlib,json,subprocess
from pathlib import Path
from datetime import datetime,timezone
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development');source=dev/'native'
board='MORI_Interface_C3.kicad_pcb';study=dev/'evidence/R185_study'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert not study.exists() and sha(source/board)==expected
status=read(dev/'STATUS.json');assert status['revision']=='C3 R181C' and status['unconnected_items']==19
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert commit=='ee73c726b994847be0094b97978e267b6ed14743'
remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],text=True).split()[0]
members=read(dev/'evidence/R184_study/archive_manifest.json')['source_non_PCB_members']
assert len(members)==77 and all(sha(source/n)==h for n,h in members.items())
rows=[]
for letter in 'ABCDEFGHIJ':
    rev='R185'+letter;d=read(b/(rev+'-drc.json'));a=read(b/(rev+'-audit.json'))
    assert a['baseline_sha256']==expected and a['board_sha256']==sha(b/rev/board)
    check=b/(rev+'-checks/result.json')
    rows.append(dict(revision=rev,board_sha256=a['board_sha256'],unconnected_items=len(d['unconnected_items']),
                     other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),
                     DRC_types=dict(collections.Counter(r['type'] for r in d['violations'])),
                     enabled_ERC=read(check)['erc_violations'] if check.exists() else 'NOT_RERUN',
                     power_checks_pass=sum(r['status']=='PASS' for r in a['power_width']),
                     power_failures=[dict(net=r['net'],width_mm=r['width_mm']) for r in a['power_width'] if r['status']!='PASS'],
                     GND_group_sizes=[len(g) for g in a['GND_groups']],critical_adjacency_pass=sum(r['status']=='PASS' for r in a['critical_placement']),
                     old_connection_loss_nets=[r['net'] for r in a['lost_pad_connections']],old_reference_losses=a['retained_trace_reference_loss'],
                     new_reference_gap_count=sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers']>1e-6 for r in a['new_copper_review']),
                     transition_flags=sum(r['status']=='FAIL' for r in a['reference_transitions']),adopted=False))
full=read(b/'R185I-checks/result.json');delta=read(b/'R185I-planned-delta.json');geometry=read(b/'R185I-geometry-review.json')
assert (full['unconnected_items'],full['violations'],full['schematic_parity'],full['erc_violations'],full['historical_transition_flags'])==(19,0,0,0,5)
assert delta['status']=='PASS' and len(delta['checks'])==2508 and not delta['errors']
assert read(b/'R185-ground-move-controls-v2.json')['status']=='PASS'
assert read(b/'R185-previous-R181C-replay.json')['status']=='PASS'
assert all(sha(source/n)==sha(b/'R185I'/n)==h for n,h in members.items())
study.mkdir();payloads=[];omitted=[]
def write(name,obj):
    with (study/name).open('x') as f:json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')
def preserve(p,rel):
    raw=p.read_bytes();compressed=p.suffix in ['.kicad_pcb','.kicad_prl'] or (len(raw)>524288 and p.suffix not in ['.png','.pdf','.npz'])
    dst=study/rel
    if compressed:dst=dst.with_name(dst.name+'.gz')
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open('xb') as f:f.write(gzip.compress(raw,mtime=0) if compressed else raw)
    payloads.append(dict(path=dst.relative_to(study).as_posix(),sha256=sha(dst),source_sha256=hashlib.sha256(raw).hexdigest(),source_bytes=len(raw),gzip=compressed))
roots=[b/r['revision'] for r in rows]
for top in sorted(b.glob('R185*')):
    for p in ([top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())):
        owner=next((root for root in roots if p.is_relative_to(root)),None);rel=p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p)==members[rel]:omitted.append(dict(local_path=p.relative_to(b).as_posix(),source_member=rel,sha256=sha(p)));continue
        preserve(p,Path('raw')/p.relative_to(b))
for p in sorted((dev/'scripts').glob('*.py')):preserve(p,Path('raw/helpers')/p.name)
for name in ['R138_joint_search.py','R167_joint_pose_screen.py','R153_run_trial.py','R184_route.py','R184_power_group_geometry.py']:
    preserve(b/name,Path('raw/helpers')/name)
preserve(source/board,Path('source_R181C.kicad_pcb'));preserve(dev/'STATUS.json',Path('STATUS.before_R185.json'))
viewed=[b/'R185-local-views'/n for n in ['source-B.png','source-In3.png','B-In3.png']]
viewed += [b/'R185I-views'/(ly+'.png') for ly in ['F.Cu','In1.Cu','In2.Cu','In3.Cu','In4.Cu','B.Cu']]
assert len(viewed)==9 and all(p.exists() for p in viewed)
write('visual_review.json',dict(images_actually_viewed=[dict(path='raw/'+p.relative_to(b).as_posix(),sha256=sha(p)) for p in viewed],
    scope='Three source/B local comparisons and six I copper-layer views, window x54-61/y5-11 mm. Native geometry plots, not GUI captures or physical images.',
    decision='No board adoption. I passes digital regression but retains a new unshielded TVS/3V3 projection; J avoids that projection but creates a new reference deficit and greater adjacent-layer HEAD_OE overlap.',
    observations=[
      'C601 return in I is a straight 0.925 mm B trace, compared with the original 1.719975 mm two-segment return. The same GND via UUID is retained at (57.9,8.4).',
      'I has a 2.793503 mm, 0.50 mm In2 supply bridge and one new 3V3 via at (57.2,8.05). All original GND identities, source connections and 50 power screens remain, but the layout is not qualified.',
      'I has no mounted-face nominal-body intersection. Its In2 route and In3 HEAD_OE overlap by 0.1031798 mm2 with no intervening ground layer; do not claim they are shielded by a ground layer between In2 and In3.',
      'I projects beneath front-side UPS_BAT/TVS copper. A 0.0134372 mm2 portion lacks intervening In1 ground, within the local supply-transfer region. Complete transient/thermal assessment is open; this is not a measured fault.',
      'J is not visually reviewed here. Its geometry audit confirms zero unshielded front UPS_BAT projection, but the native new-reference deficit is 0.00105835 mm2, and adjacent-layer HEAD_OE overlap rises to 0.3010551 mm2.'
    ],local_coupling_review='OPEN',whole_board='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False))
write('corrections.json',dict(items=[
    'The blanket source GND-position freeze was an early tool restriction, not a user instruction or native rule. Actual chat/AGENTS review is preserved; original native rules and project quality requirements remain.',
    'Requiring a moved GND annulus to be entirely inside the OLD reference fill was a conservative planning proxy. H/I instead check actual post-refill two-plane attachment. Rechecking the five other nearest-via studies with prospective contact still found no candidate in that finite scope.',
    'The first unguarded 1.45 mm bridge C restored pad connections but not the original full-width power paths, degraded HEAD_VM and added a transition flag. Endpoint centering was also wrong; C is rejected.',
    'D/F demonstrate that analytical circular antipad distance alone misses native minimum-copper fill behavior between neighboring holes. Neither the old-reference area threshold nor native rules were changed.',
    'E violates the existing D1801 via keepout. G removes the reference deficit but leaves only 0.15 mm track/via clearance. H/I combine the ground and supply moves to satisfy native 0.20 mm clearance; no rule waiver.',
    'I is a fully checked independent candidate, not the canonical board. Its 5 transition flags must not replace the canonical count of 6.',
    'The extra 2 um planning margin in the exit-position screen rejects the known exact-0.20 mm segment in every pose. Independently, the TVS and reference constraints have no joint zero-deficit pose in that sampled family; do not present the planning-margin failure as a native DRC violation.',
    'A metadata read attempted the unavailable FOOTPRINT.GetProperties method. It was retried read-only with GetValue; no PCB was saved by that query.'
]))
write('summary.json',dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(),source_commit=commit,remote_main=remote,source_revision='R181C',source_sha256=expected,
    adopted_revision=None,candidates=rows,fully_checked_independent_candidate='R185I',full_verification=full,planned_delta_status=delta['status'],planned_delta_checks=len(delta['checks']),
    ground_move_controls=read(b/'R185-ground-move-controls-v2.json'),previous_plan_replay_checks=len(read(b/'R185-previous-R181C-replay.json')['checks']),
    retained_transfer_placement=read(b/'R185-retained-transfer-pairs.json'),
    constraint_correction='Original GND via positions are not an immutable user constraint. Explicit reviewed movement retains UUID/net/padstack, declared direct returns, native rules, connectivity and all source power/reference checks.',
    unresolved_local_projection=dict(I_unshielded_TVS_mm2=.013437152290735922,I_adjacent_In3_HEAD_OE_mm2=.1031797931345143,J_adjacent_In3_HEAD_OE_mm2=.3010550895327682),
    next_step='Continue from canonical R181C. Compare the C601 supply/ground transfer and neighboring HEAD_OE/DISARMED breakout as a coordinated group; a fixed-endpoint bridge is insufficient in the reviewed finite window. Keep I as an independent candidate, not a released solution. For clamp/reset placement retain the actual SOURCE/VCAP lands and C1601 feed; expand to control/source breakout rather than repeat the old isolated clamp poses.',
    space_finding='Local supply, return, native keepout and control-reference constraints interact. Neither finite failures nor a digital PASS prove the 70x35 board globally unroutable, expanded 70x40 sufficient, or engineering complete.',
    outline_direction='R182 70x40 direction question remains unanswered and unadopted. Current 70x35 outline and fixed interfaces unchanged.',
    accepted_revision_unchanged='R181C',accepted_transition_flags=6,remaining_unconnected_items=19,newly_completed_connections_in_accepted_board=0,
    whole_board_visual='NOT_TESTED',manufacturer_layout_qualification='NOT_TESTED',physical='NOT_TESTED',manufacturing_release=False,goal_complete=False))
write('archive_manifest.json',dict(scope=__doc__,payloads=payloads,source_non_PCB_members=members,unchanged_native_members_omitted=omitted,
    dependencies=[dict(path='../R182_study/raw/R182-supply-reservations/result.json',sha256=sha(b/'R182-supply-reservations/result.json'),source_sha256=expected),
                  dict(path='../R184_study/archive_manifest.json',sha256=sha(dev/'evidence/R184_study/archive_manifest.json'),usage='Retained-transfer placement uses R184 power-group pose payloads and helpers.')],
    reconstruction='Restore source_R181C PCB and source_commit native members in a separate checkout, then restore raw trial files and recorded frozen R182/R184 dependencies. The current source remains R181C. R185I checks restore original project metadata; other native trials may retain captured KiCad default normalization. No manufacturing export.',
    original_local_sources_preserved=True))
for row in payloads:
    data=(study/row['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==row['sha256'];raw=gzip.decompress(data) if row['gzip'] else data
    assert len(raw)==row['source_bytes'] and hashlib.sha256(raw).hexdigest()==row['source_sha256']
assert sha(source/board)==expected and all(sha(source/n)==h for n,h in members.items())
write('archive_verification.json',dict(status='PASS',payload_count=len(payloads),native_DRC_checked_trials=10,full_DRC_ERC_planned_review_trials=1,
    all_original_byte_hashes_match=True,protected_non_PCB_members_unchanged=77,accepted_source_unchanged=True,actual_viewed_image_count=9,local_originals_preserved=True))
status.update(last_followup_study='R185',latest_study_evidence='evidence/R185_study/summary.json',latest_study_adopted=False,
    latest_study_note='Explicit GND movement is now source-bound and return-path checked. Independent I passes 2508 checks and reduces transition flags to 5, but TVS/adjacent-layer coupling review remains open; J introduces a new reference gap. No PCB adoption: R181C remains at 19 opens and 6 historical flags.',
    ground_via_move_policy='Native rules/keepouts remain. Original GND positions are not blanket-frozen; move_ground_vias requires exact UUID/net/padstack, source contact inventory, non-lengthened/nonnarrowed declared direct returns, actual plane attachment and all source electrical/reference checks.')
(dev/'STATUS.json').write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(dict(status='PASS',payloads=len(payloads),accepted_revision='R181C',opens=19,transition_flags=6,adopted=False)))
