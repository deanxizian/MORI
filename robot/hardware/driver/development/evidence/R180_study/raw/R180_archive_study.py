"""Freeze R180 joint-terminal experiments without changing the accepted PCB.

All original local trial files remain. No manufacturing or physical release.
"""
import collections
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
source = dev / 'native'
study = dev / 'evidence/R180_study'
board = 'MORI_Interface_C3.kicad_pcb'
source_sha = '0314affe1179898dbb679292c8c4ecb8f59838d5753302436854bf4ea5e76af9'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def write(path, value):
    with path.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

assert not study.exists()
assert sha(source / board) == source_sha
assert (source / board).read_bytes().startswith(b'(kicad_pcb')
status = read(dev / 'STATUS.json')
assert status['revision'] == 'C3 R179I' and status['unconnected_items'] == 19
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert commit == 'f95a7f2b9b0a6c402156e6341003fa88fa9e90ac'
remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/main'], text=True).split()[0]
source_all = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
members = {x['member']: x['sha256'] for x in read(dev / 'evidence/R179I/adoption.json')['member_checks']}
assert len(members) == 77 and all(sha(source / n) == h for n, h in members.items())

rows = []
for letter in 'ABCDEFGHIJKLMNOPQRST':
    rev = 'R180' + letter
    plan = read(b / (rev + '-plan.json'))
    assert plan['board_sha256'] == source_sha
    if letter == 'F':
        commands = read(b / (rev + '-commands.json'))
        assert commands[0]['returncode'] == 1 and not (b / (rev + '-drc.json')).exists()
        rows.append(dict(revision=rev, native_build='FAIL', reason='C301 combined body/via guard cannot use the separate-guard reconstruction mode; corrected in G.', adopted=False, enabled_ERC='NOT_RUN'))
        continue
    d = read(b / (rev + '-drc.json'))
    a = read(b / (rev + '-audit.json'))
    assert a['board_sha256'] == sha(b / rev / board)
    assert a['baseline_sha256'] == source_sha
    check = b / (rev + '-checks/result.json')
    rows.append(dict(
        revision=rev, native_build='PASS', board_sha256=a['board_sha256'],
        unconnected_items=len(d['unconnected_items']), other_DRC=len(d['violations']),
        DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),
        schematic_parity=len(d['schematic_parity']),
        enabled_ERC=read(check)['erc_violations'] if check.exists() else 'NOT_RERUN',
        power_checks_pass=sum(x['status'] == 'PASS' for x in a['power_width']),
        power_check_count=len(a['power_width']), GND_group_sizes=[len(x) for x in a['GND_groups']],
        critical_adjacency_pass=sum(x['status'] == 'PASS' for x in a['critical_placement']),
        old_connection_loss_nets=[x['net'] for x in a['lost_pad_connections']],
        old_reference_losses=len(a['retained_trace_reference_loss']),
        new_reference_gaps=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] > 1e-6 for x in a['new_copper_review']),
        adopted=False))

r = read(b / 'R180R-checks/result.json')
a = read(b / 'R180R-checks/regression.json')
delta = read(b / 'R180R-planned-delta.json')
inspection = read(b / 'R180R-inspection.json')
assert (r['unconnected_items'], r['violations'], r['schematic_parity'], r['erc_violations']) == (19, 2, 0, 0)
assert r['board_sha256'] == sha(b / 'R180R' / board)
assert delta['status'] == 'FAIL' and delta['errors'] == ['all_prior_pad_connections']
assert len(delta['checks']) == 2594
assert all(x['status'] == 'PASS' for x in a['power_width']) and len(a['power_width']) == 50
assert all(x['status'] == 'PASS' for x in a['critical_placement']) and len(a['critical_placement']) == 63
assert [len(x) for x in a['GND_groups']] == [155]
assert not a['retained_trace_reference_loss'] and r['new_reference_gaps'] == 0
assert inspection['source_ground_vias_preserved'] == 114
assert len(inspection['same_face_nominal_body_hits']) == 2
assert all(x['component'] == 'J102' for x in inspection['same_face_nominal_body_hits'])
assert not a['changed_project_members']

viewed = ['R180A-U301-B.png', 'R180L-U301-B.png', 'R180R-U301-B.png', 'R180R-U301-F.png', 'R180R-U301-In3.png']
assert all((b / n).is_file() for n in viewed)
study.mkdir()
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

roots = [b / ('R180' + letter) for letter in 'ABCDEFGHIJKLMNOPQRST']
for top in sorted(b.glob('R180*')):
    files = [top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())
    for path in files:
        owner = next((root for root in roots if path.is_relative_to(root)), None)
        rel = path.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(path) == members[rel]:
            omitted.append(dict(local_path=path.relative_to(b).as_posix(), source_member=rel, sha256=sha(path)))
            continue
        preserve(path, Path('raw') / path.relative_to(b))
for path in sorted((dev / 'scripts').glob('*.py')):
    preserve(path, Path('raw/helpers') / path.name)
for name in ['R138_joint_search.py', 'R152_render_highlight.py', 'R153_run_trial.py', 'R161R_inspection.py', 'R162_inspection.py', 'R167_joint_pose_screen.py']:
    preserve(b / name, Path('raw/helpers') / name)
preserve(source / board, Path('source_R179I.kicad_pcb'))
preserve(dev / 'STATUS.json', Path('STATUS.before_R180.json'))

now = datetime.now(timezone.utc).isoformat()
write(study / 'visual_review.json', dict(
    source_sha256=source_sha, candidate_sha256=r['board_sha256'], candidate='R180R',
    scope='Five listed native diagnostic images were viewed. These are renders of actual native copper, not GUI screenshots or a whole-board review.',
    images_actually_viewed=[dict(path='raw/' + name, sha256=sha(b / name)) for name in viewed],
    observations=[
        'R180R DISARMED lower-right pad is enclosed by its body, the new CLR wrap and the nearby source power/reference void. The strict raster source region is only 70 cells at 0.05 mm, with no legal new via site.',
        'R180R F view confirms the L701 switching pad and nearby C702 input pad occupy candidate through-via locations. Empty B copper alone does not establish a through-via opportunity.',
        'R180R In3 view confirms the nearby retained diagonal belongs to ACT_CURRENT_ADC; it is not a regulator feedback trace.',
        'Inspection reports two new ARMED F-segment projections into the nominal J102 body near (36,6), total 0.027663486706764866 mm2. This is an unresolved same-face routing defect, not waived by native DRC.',
        'S/T retire the old CLR In2 branch and reassign its fixed via to ARMED. Restoring DISARMED in T blocks both subsequent ARMED and CLR proposals; independent proposals cannot be combined blindly.'
    ],
    local_acceptance='FAIL', opposite_face_coupling_thermal='NOT_TESTED', whole_board_visual='NOT_TESTED', physical='NOT_TESTED', adopted=False, manufacturing_release=False))
write(study / 'summary.json', dict(
    recorded_at_utc=now, source_commit=commit, remote_main=remote,
    source_revision='R179I', source_sha256=source_sha, adopted_revision=None,
    candidates=rows, completed_native_trials=19, failed_native_builds=1,
    detailed_incomplete_candidate='R180R', full_verification=r,
    planned_delta_status=delta['status'], planned_checks=len(delta['checks']), planned_delta_errors=delta['errors'],
    source_ground_vias_preserved_in_R=114, R_unchanged_non_PCB_members=77,
    accepted_revision_unchanged='R179I', remaining_unconnected_items=19,
    newly_completed_connections_in_accepted_board=0, baseline_unconnected_items=40,
    remaining_connectivity_fraction=.475, connectivity_fraction_is_not_engineering_progress=True,
    space_finding='Actual local escape/via congestion, with native pad conflicts, reference-ground voids and conflicting ARMED/CLR/DISARMED topology. Not a proof that the entire fixed outline is unroutable or must be enlarged.',
    next_step='Use the explicit Q/R and S/T barriers to compare a different grouped U301/C301/CLK/power escape topology; do not repeat independent fixed-pose searches or adopt a candidate that loses original connections. Check J102 mounted-face escape before accepting any restored ARMED route.',
    whole_board_visual='NOT_TESTED', physical='NOT_TESTED', manufacturing_release=False, goal_complete=False))
write(study / 'archive_manifest.json', dict(
    scope=__doc__, payloads=payloads, source_non_PCB_members=members,
    unchanged_native_members_omitted=omitted,
    reconstruction='Use source commit native members matched by SHA, then restore the desired raw/R180X board and any nonidentical project member. R180F is a failed build copy, not a completed candidate.',
    original_local_sources_preserved=True))
for row in payloads:
    path = study / row['path']
    assert sha(path) == row['sha256']
    data = gzip.decompress(path.read_bytes()) if row['gzip'] else path.read_bytes()
    assert len(data) == row['source_bytes'] and hashlib.sha256(data).hexdigest() == row['source_sha256']
assert source_all == {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
write(study / 'archive_verification.json', dict(status='PASS', payload_count=len(payloads), completed_native_trials=19, failed_builds_preserved=1, all_original_byte_hashes_match=True, source_native_members_unchanged=True, local_originals_preserved=True, actual_viewed_image_count=5))
status.update(last_followup_study='R180', latest_study_evidence='evidence/R180_study/summary.json', latest_study_adopted=False,
              latest_study_note='Joint U301/C301 trials restore subsets only. R has 19 opens but loses original DISARMED and has two dangling vias plus J102 mounted-face projection defects; T restores DISARMED but blocks CLR and ARMED. No R180 candidate adopted; R179I and 19 opens remain.', goal_complete=False)
(dev / 'STATUS.json').write_text(json.dumps(status, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(dict(archived='R180_study', payload_count=len(payloads), accepted_board_unchanged='R179I', completed_native_trials=19, adopted=False, goal_complete=False)), flush=True)
