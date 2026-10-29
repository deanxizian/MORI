"""Freeze the unfinished R190 studies for a progress publication; adopt no PCB."""
import collections
import copy
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
source = dev / 'native'
study = dev / 'evidence/R190_study'
board = 'MORI_Interface_C3.kicad_pcb'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = 'b6da4de8fc7341e01971efb11f1720f6cdf68364958675948ef76ef03830722a'
assert not study.exists() and sha(source / board) == expected
status = read(dev / 'STATUS.json')
assert status['revision'] == 'C3 R188C' and status['unconnected_items'] == 19
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert commit == '5993af7dd1e4b5ef027cd210a91133ee3ad35f39'
members = {r['member']: r['sha256'] for r in read(dev / 'evidence/R188C/adoption.json')['member_checks']}
assert len(members) == 77 and all(sha(source / n) == h for n, h in members.items())
roots = [b / ('R190' + letter) for letter in 'ABC']
rows = []
for root in roots:
    rev = root.name
    d = read(b / (rev + '-drc.json'))
    a = read(b / (rev + '-audit.json'))
    assert a['baseline_sha256'] == expected and a['board_sha256'] == sha(root / board)
    differences = [n for n, h in members.items() if sha(root / n) != h]
    assert differences == ['MORI_Interface_C3.kicad_pro']
    normalized = read(root / differences[0])
    original = read(source / differences[0])
    allowed = copy.deepcopy(original)
    for item in allowed['board']['design_settings']['teardrop_parameters']:
        item.setdefault('td_enabled', False)
    for key in ['net_colors', 'netclass_assignments']:
        if allowed['net_settings'][key] is None:
            allowed['net_settings'][key] = {}
    assert normalized == allowed
    rows.append(dict(
        revision=rev, board_sha256=a['board_sha256'],
        unconnected_items=len(d['unconnected_items']), other_DRC=len(d['violations']),
        schematic_parity=len(d['schematic_parity']), enabled_ERC='NOT_RERUN',
        DRC_types=dict(collections.Counter(x['type'] for x in d['violations'])),
        power_checks_pass=sum(r['status'] == 'PASS' for r in a['power_width']),
        GND_group_sizes=[len(g) for g in a['GND_groups']],
        critical_adjacency_pass=sum(r['status'] == 'PASS' for r in a['critical_placement']),
        old_connection_loss_nets=[r['net'] for r in a['lost_pad_connections']],
        old_reference_losses=a['retained_trace_reference_loss'],
        new_reference_gap_count=sum(r['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] > 1e-6 for r in a['new_copper_review']),
        transition_flags=sum(r['status'] == 'FAIL' for r in a['reference_transitions']),
        project_normalization=dict(source_sha256=sha(source / differences[0]),
                                   normalized_sha256=sha(root / differences[0]),
                                   semantic_changes=['disabled teardrop defaults', 'empty net_colors map', 'empty netclass_assignments map'],
                                   restored=False, normalized_original_preserved=True),
        exact_planned_delta_review='NOT_RUN', candidate_visual_review='NOT_TESTED',
        full_coupling_review='NOT_TESTED', adopted=False))
assert [(r['unconnected_items'], r['other_DRC'], r['power_checks_pass']) for r in rows] == [(19, 2, 50), (19, 0, 50), (20, 6, 43)]
assert not rows[1]['old_connection_loss_nets'] and not rows[1]['old_reference_losses'] and rows[1]['new_reference_gap_count'] == 0
survey = read(b / 'R190B-reference-survey.json')
assert survey['source_sha256'] == rows[1]['board_sha256'] and (survey['flagged_tracks'], survey['flagged_nets']) == (74, 35)
study.mkdir()
payloads = []
omitted = []
def write(name, obj):
    with (study / name).open('x') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write('\n')
def preserve(p, rel):
    raw = p.read_bytes()
    compressed = p.suffix in ['.kicad_pcb', '.kicad_prl'] or (len(raw) > 524288 and p.suffix not in ['.png', '.pdf', '.npz'])
    dst = study / rel
    if compressed:
        dst = dst.with_name(dst.name + '.gz')
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open('xb') as f:
        f.write(gzip.compress(raw, mtime=0) if compressed else raw)
    payloads.append(dict(path=dst.relative_to(study).as_posix(), sha256=sha(dst), source_sha256=hashlib.sha256(raw).hexdigest(), source_bytes=len(raw), gzip=compressed))
for top in sorted(b.glob('R190*')):
    for p in ([top] if top.is_file() else sorted(p for p in top.rglob('*') if p.is_file())):
        owner = next((root for root in roots if p.is_relative_to(root)), None)
        rel = p.relative_to(owner).as_posix() if owner else None
        if rel in members and sha(p) == members[rel]:
            omitted.append(dict(local_path=p.relative_to(b).as_posix(), source_member=rel, sha256=sha(p)))
            continue
        preserve(p, Path('raw') / p.relative_to(b))
for p in sorted((dev / 'scripts').glob('*.py')):
    preserve(p, Path('raw/helpers') / p.name)
for name in ['R138_joint_search.py', 'R167_joint_pose_screen.py', 'R153_run_trial.py']:
    preserve(b / name, Path('raw/helpers') / name)
preserve(source / board, Path('source_R188C.kicad_pcb'))
preserve(dev / 'STATUS.json', Path('STATUS.before_R190.json'))
decision = dict(adopted=False, status_note='R190 A/B/C are archived, not adopted. B restores local five-resistor connectivity with 19 opens and zero other native DRC, but exact-delta, ERC, visual and complete coupling review remain unfinished. C closes RAW but loses CAM/3V3 power connectivity and fails native DRC. Canonical R188C remains unchanged.',
                space_authorization=dict(user_statement='允许评估 70×40 mm 的机械空间',
                                         scope='Independent mechanical-space assessment with fixed mounting holes and interfaces only.',
                                         assessment='NOT_TESTED', adoption=False, main_model_changed=False))
write('summary.json', dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), source_commit=commit,
    source_revision='R188C', source_sha256=expected, adopted_revision=None, candidates=rows,
    decision=decision, accepted_revision_unchanged='R188C', remaining_unconnected_items=19,
    accepted_transition_flags=6, canonical_reference_queue=dict(flagged_tracks=75, flagged_nets=36),
    candidate_B_reference_survey=dict(reviewed_tracks=survey['non_GND_tracks_reviewed'], flagged_tracks=74, flagged_nets=35),
    whole_board_visual='NOT_TESTED', manufacturer_layout_qualification='NOT_TESTED', physical='NOT_TESTED',
    manufacturing_release=False, goal_complete=False))
write('archive_manifest.json', dict(scope=__doc__, payloads=payloads, source_non_PCB_members=members,
    unchanged_native_members_omitted=omitted,
    dependencies=[dict(path='../R188_study/raw/R188-supply-reservations/result.json', sha256=sha(b / 'R188-supply-reservations/result.json'), source_sha256=expected)],
    reconstruction='Restore the frozen source PCB and the 77 source_commit native members into an independent checkout; restore raw candidate files, scripts and linked supply reservations. Candidate project metadata is preserved as produced by KiCad; no candidate is adopted.',
    original_local_sources_preserved=True))
for r in payloads:
    data = (study / r['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == r['sha256']
    raw = gzip.decompress(data) if r['gzip'] else data
    assert len(raw) == r['source_bytes'] and hashlib.sha256(raw).hexdigest() == r['source_sha256']
assert sha(source / board) == expected and all(sha(source / n) == h for n, h in members.items())
write('archive_verification.json', dict(status='PASS', payload_count=len(payloads), native_DRC_checked_trials=3,
    all_original_byte_hashes_match=True, protected_non_PCB_members_unchanged=77, accepted_source_unchanged=True,
    candidate_visual_review='NOT_TESTED', local_originals_preserved=True))
status.update(last_followup_study='R190', latest_study_evidence='evidence/R190_study/summary.json',
              latest_study_adopted=False, latest_study_note=decision['status_note'],
              board_space_assessment_authorization=decision['space_authorization'])
(dev / 'STATUS.json').write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(dict(status='PASS', payloads=len(payloads), native_trials=3, accepted_revision='R188C', opens=19, adopted=False)))
