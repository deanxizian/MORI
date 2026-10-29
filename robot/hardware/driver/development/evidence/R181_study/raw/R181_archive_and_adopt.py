"""Freeze R181 A-H and receive only C as local routing preparation.

No additional open is closed. U301 changes, manufacturing and physical release
are not adopted. Original local trials and source native members are preserved.
"""
import collections
import csv
import gzip
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
source, candidate = dev / 'native', b / 'R181C'
study, evidence = dev / 'evidence/R181_study', dev / 'evidence/R181C'
backup = Path('robot/.state/c3-completion/baseline_R179I_before_R181C')
board = 'MORI_Interface_C3.kicad_pcb'
old = '0314affe1179898dbb679292c8c4ecb8f59838d5753302436854bf4ea5e76af9'
new = '13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


assert not study.exists() and not evidence.exists() and not backup.exists()
assert sha(source / board) == old and sha(candidate / board) == new
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert commit == 'e3b344147dafe2390169c46239c7a20802edc2b4'
remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/main'], text=True).split()[0]
r = read(b / 'R181C-checks/result.json')
reg = read(b / 'R181C-checks/regression.json')
delta = read(b / 'R181C-planned-delta.json')
inspection = read(b / 'R181C-inspection.json')
geometry = read(b / 'R181C-geometry-review.json')
assert tuple(r[k] for k in ['board_sha256', 'unconnected_items', 'violations', 'schematic_parity', 'erc_violations', 'new_reference_gaps', 'historical_transition_flags']) == (new, 19, 0, 0, 0, 0, 6)
assert r['ina300_rlimit_return_screen'] == 'PASS'
assert delta['status'] == 'PASS' and not delta['errors'] and len(delta['checks']) == 2523
assert delta['source_sha256'] == old and delta['candidate_sha256'] == new
assert not reg['lost_pad_connections'] and not reg['retained_trace_reference_loss'] and not reg['changed_project_members']
assert len(reg['power_width']) == 50 and all(x['status'] == 'PASS' for x in reg['power_width'])
assert len(reg['critical_placement']) == 63 and all(x['status'] == 'PASS' for x in reg['critical_placement'])
assert [len(x) for x in reg['GND_groups']] == [155]
assert not inspection['same_face_nominal_body_hits'] and inspection['source_ground_vias_preserved'] == 114
assert geometry['source_sha256'] == old and geometry['candidate_sha256'] == new
assert geometry['track_counts'] == dict(before=1409, after=1409)
assert geometry['via_counts'] == dict(before=325, after=324)
assert geometry['new_holes'] == 0 and geometry['retained_vias_unchanged'] == 324
assert geometry['original_ground_vias_preserved'] == 114
assert all(x['unshielded_by_In1_mm2'] < 1e-8 for x in geometry['opposite_body_projection_review'] + geometry['foreign_copper_projection_review'])
assert len(geometry['reused_transfer_return_review']) == 2 and all(x['status'] == 'PASS' for x in geometry['reused_transfer_return_review'])
assert abs(geometry['nearby_same_face_foreign_copper'][0]['copper_edge_distance_mm'] - .2225) < 1e-8
members = {x['member']: x['sha256'] for x in read(dev / 'evidence/R179I/adoption.json')['member_checks']}
assert len(members) == 77 and all(sha(source / n) == sha(candidate / n) == h for n, h in members.items())
source_all = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
status = read(dev / 'STATUS.json')
assert status['revision'] == 'C3 R179I' and status['unconnected_items'] == 19
now = datetime.now(timezone.utc).isoformat()

images = [dict(path='images/' + p.name, sha256=sha(p)) for p in sorted((b / 'R181C-views').glob('*.png'))]
assert len(images) == 8
visual = dict(
    source_sha256=old, board_sha256=new, local_status='PASS',
    scope='Six actual native local copper layer views and two immutable source comparisons were viewed. Local prototype geometry only; all eight were re-viewed before adoption.',
    images_actually_viewed=images,
    decision='Receive only C: replace thirteen S2/WHEEL_sense segments by thirteen F segments and retire one obsolete non-ground via. No footprint, U301/C301 pose, power feed, native rule or keepout change.',
    observations=[
        'The F branch avoids mounted-face nominal bodies and the Q1602 drain pads, then passes above Q1602 toward the retained R1002 transfer. The old F stub and unused transfer at (45.6,9.35) are removed.',
        'The old diagonal S2 branch on In3 is gone, freeing a local corridor. This alone does not establish a valid ARMED route: E cuts the MOTION_3V3 supply into two pad groups.',
        'The In1 reference plane covers the new route outside its own transfer clearances. The two reused transfers retain nearby GND vias at about 0.716 and 0.721 mm; no new transition warning is introduced.',
        'B U1001 and R303 body projections and the recorded internal/outer foreign-copper projections have intervening In1 ground in this geometric screen. They are not body keepout violations under the user clarification.',
        'Minimum same-face copper edge distances are 0.2225 mm to Q1602 drain pads and 0.375 mm to C707.1. These are nominal native geometry, not manufacturing tolerances, measured crosstalk or thermal margins.',
        'G attempts more MOSFET separation but shorts the CAM regulator trace/pad. H removes two small route offsets but loses reference coverage in two areas (0.0080647 and 0.0336962 mm2). Their cleaner appearance cannot replace electrical acceptance. C retains those offsets for reference continuity.'
    ],
    geometry_review='geometry_review.json',
    full_noise_transient_thermal='NOT_TESTED', whole_board_visual='NOT_TESTED', whole_board_route_style='NOT_TESTED',
    physical='NOT_TESTED', manufacturing_release=False)
write(b / 'R181C-visual-review.json', visual)
write(b / 'R181-diagnostic-corrections.json', dict(
    geometry_review_v1='Read-only script failed before output with missing box import; original script and traceback retained.',
    geometry_review_v2='Read-only script failed before output with missing polygonize import; original script and traceback retained.',
    geometry_review_final='Imports corrected; completed with source/candidate hashes and no native board writes.',
    existing_transfer='All six via annuli at (23,8.6) are already flashed. No missing via-layer activation bug was found.',
    F_via='The guessed (23.8,15) via conflicts with actual UPS_5V/C701/C702 copper and holes. Do not reuse as a screened safe site.',
    adopted_U301_relocation=False))

study.mkdir()
evidence.mkdir()
for p in (b / 'R181C-checks').iterdir():
    shutil.copy2(p, evidence / p.name)
for src, dst in [('R181C-plan.json', 'plan.json'), ('R181C-planned-delta.json', 'planned-delta.json'), ('R181C-inspection.json', 'inspection.json'), ('R181C-geometry-review.json', 'geometry_review.json'), ('R181C-visual-review.json', 'visual_review.json'), ('R181C-commands.json', 'build_commands.json')]:
    shutil.copy2(b / src, evidence / dst)
shutil.copytree(b / 'R181C-views', evidence / 'images')
(evidence / 'source_R179I.kicad_pcb.gz').write_bytes(gzip.compress((source / board).read_bytes(), mtime=0))
with (evidence / 'remaining_connections.csv').open('x', newline='') as f:
    w = csv.writer(f)
    w.writerow(['item', 'description', 'endpoint_descriptions'])
    for i, q in enumerate(read(evidence / 'drc.json')['unconnected_items'], 1):
        w.writerow([i, q['description'], ' | '.join(x['description'] for x in q['items'])])

rows = []
for letter in 'ABCDEFGH':
    rev = 'R181' + letter
    d, a = read(b / (rev + '-drc.json')), read(b / (rev + '-audit.json'))
    assert a['board_sha256'] == sha(b / rev / board) and a['baseline_sha256'] == old
    assert read(b / (rev + '-plan.json'))['board_sha256'] == old
    check = b / (rev + '-checks/result.json')
    rows.append(dict(revision=rev, board_sha256=a['board_sha256'], unconnected_items=len(d['unconnected_items']),
                     other_DRC=len(d['violations']), schematic_parity=len(d['schematic_parity']),
                     DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),
                     enabled_ERC=read(check)['erc_violations'] if check.exists() else 'NOT_RERUN',
                     power_checks_pass=sum(x['status'] == 'PASS' for x in a['power_width']),
                     power_check_count=len(a['power_width']), GND_group_sizes=[len(x) for x in a['GND_groups']],
                     critical_adjacency_pass=sum(x['status'] == 'PASS' for x in a['critical_placement']),
                     old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],
                     old_reference_losses=len(a['retained_trace_reference_loss']),
                     new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] > 1e-6 for x in a['new_copper_review']),
                     adopted=letter == 'C'))

payloads, omitted = [], []


def preserve(path, relative):
    data = path.read_bytes()
    compressed = path.suffix in ['.kicad_pcb', '.kicad_prl'] or (len(data) > 524288 and path.suffix not in ['.png', '.pdf'])
    target = study / relative
    if compressed:
        target = target.with_name(target.name + '.gz')
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists()
    target.write_bytes(gzip.compress(data, mtime=0) if compressed else data)
    payloads.append(dict(path=target.relative_to(study).as_posix(), sha256=sha(target), source_sha256=hashlib.sha256(data).hexdigest(), source_bytes=len(data), gzip=compressed))


roots = [b / q['revision'] for q in rows]
extra = ['R180S-R180-displaced-R181-transfer-probe', 'R180T-R181-plane-armed', 'R180T-R181-plane-armed-regions', 'R180T-R181-plane-armed-barriers', 'R180-supply-reservations']
for top in sorted(list(b.glob('R181*')) + [b / name for name in extra]):
    assert top.exists()
    if top.name == 'R181C-views':
        continue
    files = [top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
    for p in files:
        owner = next((root for root in roots if p.is_relative_to(root)), None)
        rel = p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p) == members[rel]:
            omitted.append(dict(local_path=p.relative_to(b).as_posix(), source_member=rel, sha256=sha(p)))
            continue
        preserve(p, Path('raw') / p.relative_to(b))
for p in sorted((dev / 'scripts').glob('*.py')):
    preserve(p, Path('raw/helpers') / p.name)
for name in ['R138_joint_search.py', 'R152_render_highlight.py', 'R153_run_trial.py', 'R161R_inspection.py', 'R162_inspection.py']:
    preserve(b / name, Path('raw/helpers') / name)
preserve(dev / 'STATUS.json', Path('STATUS.before_R181.json'))
prerequisites = []
for rev in ['R180S', 'R180T']:
    p = dev / 'evidence/R180_study/raw' / rev / (board + '.gz')
    raw = gzip.decompress(p.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == sha(b / rev / board)
    prerequisites.append(dict(path='../R180_study/raw/' + rev + '/' + board + '.gz', sha256=sha(p), source_sha256=sha(b / rev / board)))

write(study / 'summary.json', dict(
    recorded_at_utc=now, source_commit=commit, remote_main=remote, source_revision='R179I', source_sha256=old,
    adopted_revision='R181C', adopted_board_sha256=new, candidates=rows, completed_native_trials=8,
    remaining_unconnected_items=19, newly_completed_connections_in_accepted_board=0,
    baseline_unconnected_items=40, remaining_connectivity_fraction=.475, connectivity_fraction_is_not_engineering_progress=True,
    full_verification=r, planned_checks=2523, retained_source_vias_unchanged=324, source_ground_vias_preserved=114,
    explicitly_retired_obsolete_non_ground_vias=1, unchanged_non_PCB_members=77,
    space_finding='Confirmed local escape, via, reference-ground and power-plane conflicts. E cuts MOTION_3V3 into 39- and 17-pad groups; F via conflicts with existing power copper; G cannot move the sampling route left without CAM regulator shorts. Bounded failures do not prove the entire 70x35 outline unroutable or require enlargement.',
    next_step='Regenerate power reservations against adopted C; compare joint U301/C301/CLK/power escape with the 3V3 supply bridge planned before ARMED. Preserve old CLR and DISARMED and reject any solution that loses original power or ground. Do not repeat E/F/G/H geometry without changing the demonstrated constraint.',
    whole_board_visual='NOT_TESTED', physical='NOT_TESTED', manufacturing_release=False, goal_complete=False))
write(study / 'archive_manifest.json', dict(
    scope=__doc__, payloads=payloads, source_non_PCB_members=members, unchanged_native_members_omitted=omitted,
    accepted_images='../R181C/images', source_board='../R181C/source_R179I.kicad_pcb.gz', external_frozen_prerequisites=prerequisites,
    reconstruction='Restore source commit native members and source R179I board before replaying source-bound scripts; current development native is C. Restore desired raw/R181X PCB plus any nonidentical project members. R180 reservations remain bound to R179I and must not be relabeled for C.',
    original_local_sources_preserved=True))
for q in payloads:
    p = study / q['path']
    assert sha(p) == q['sha256']
    data = gzip.decompress(p.read_bytes()) if q['gzip'] else p.read_bytes()
    assert len(data) == q['source_bytes'] and hashlib.sha256(data).hexdigest() == q['source_sha256']
for q in images:
    assert sha(evidence / q['path']) == q['sha256']
assert source_all == {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
write(study / 'archive_verification.json', dict(status='PASS', payload_count=len(payloads), completed_native_trials=8,
     all_original_byte_hashes_match=True, original_local_trials_preserved=True, source_native_members_unchanged_before_adoption=True, accepted_images_hash_verified=8))

shutil.copytree(source, backup, copy_function=shutil.copy2)
assert source_all == {p.relative_to(backup).as_posix(): sha(p) for p in backup.rglob('*') if p.is_file()}
shutil.copy2(candidate / board, source / board)
assert sha(source / board) == new
for n, h in source_all.items():
    if n != board:
        assert sha(source / n) == h
write(evidence / 'adoption.json', dict(adopted_at_utc=now, source_commit=commit, source_sha256=old, adopted_board_sha256=new,
    source_full_local_backup=str(backup.absolute()), other_native_members_unchanged=77,
    member_checks=[dict(member=n, sha256=sha(source / n)) for n in members], development_only=True,
    published_revision='C3 R108P', adopted_in_main_model=False, adopted_in_software=False, engineering_status='FAIL',
    physical='NOT_TESTED', manufacturing_release=False, goal_complete=False))
status.update(r)
status.update(revision='C3 R181C', previous_candidate='C3 R179I', previous_candidate_sha256=old,
    strict_regression_explanation='Raw geometry FAIL records thirteen replaced sampling segments and one explicitly obsolete non-ground via. All 2523 exact-delta and electrical/reference checks pass; no footprint, rule or keepout change.',
    planned_delta_review_status='PASS', planned_delta_check_count=2523, electrical_regression_status='PASS',
    local_visual_review='PASS', local_visual_review_explanation='Eight native local/source views reviewed. Sampling branch shortened from 25.512702 to 18.203088 mm; opposite/internal projections have In1 ground. Actual closest Q1602 drain-pad separation is 0.2225 mm and C707.1 separation 0.375 mm; full analog/noise/transient/thermal qualification remains open. G/H alternatives fail shorts/reference checks.',
    new_same_face_nominal_body_projection_groups=0, segment_count=1409, via_count=324, footprint_count=215,
    remaining_connectivity_fraction=.475, ina300_rlimit_return_evidence='evidence/R181C/ina300-return.json',
    last_followup_study='R181', latest_study_evidence='evidence/R181_study/summary.json', latest_study_adopted=True,
    latest_study_note='Only C sampling reroute adopted; no additional open closed. E ARMED connection cuts the 3V3 supply; F/G conflict with native power copper; H simplification creates reference gaps. U301 trial movement not adopted. Actual local congestion reported, no whole-board enlargement conclusion.', goal_complete=False)
crossing = read(dev / 'evidence/R179I/coupling_review.json')['sampling_crossings']
assert len(crossing) == 1 and crossing[0]['retained_WHEEL_sense_uuid'] in read(b / 'R181C-plan.json')['delete_copper']
for item in status['open_manufacturer_layout_items']:
    if item['id'] == 'CLR_IN2_ADJACENT_SAMPLING_CROSSING':
        item['reason'] = 'The specific perpendicular CLR/In3 WHEEL_sense crossing recorded at R179I is removed by R181C retirement of ddc4005e-7631-4fed-a5eb-0f0a3f672f63. Historical evidence remains unchanged. Complete CLR noise/EMC/timing/thermal qualification remains open; this geometry change is not a qualification pass.'
        item['current_geometry_evidence'] = 'evidence/R181C/plan.json'
status['open_manufacturer_layout_items'].append(dict(id='WHEEL_SENSE_F_POWER_ADJACENCY', status='NOT_TESTED',
    reason='Local continuous-ground/body/native geometry screens pass; closest nominal Q1602 drain-pad gap 0.2225 mm and C707.1 gap 0.375 mm. Complete sampling accuracy, noise/transient coupling and thermal qualification remain open.',
    evidence='evidence/R181C/geometry_review.json'))
(dev / 'STATUS.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(adopted='R181C', board_sha256=new, remaining_unconnected_items=19, newly_completed_connections=0,
    planned_checks=2523, archive_payloads=len(payloads), unchanged_non_PCB_members=77, goal_complete=False)), flush=True)
