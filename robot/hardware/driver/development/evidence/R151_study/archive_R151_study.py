"""Archive unadopted R151 trials and transport diagnostics without changing R148E."""
import gzip
import hashlib
import json
from pathlib import Path

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
out = dev / 'evidence/R151_study'
assert not out.exists()
out.mkdir()
board = 'MORI_Interface_C3.kicad_pcb'
source = dev / 'native'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
expected = '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
assert sha(source / board) == expected
status = read(dev / 'STATUS.json')
assert status['revision'] == 'C3 R148E' and status['unconnected_items'] == 26
for x in read(dev / 'evidence/R148E/adoption.json')['member_checks']:
    assert sha(source / x['member']) == x['sha256']
dsn_audit = read(b / 'R151-dsn-diagnostic/constraint_audit.json')
assert dsn_audit['source_and_copy_unchanged']
for x in dsn_audit['native_member_checks']:
    assert sha(source / x['path']) == x['sha256']
    assert sha(b / 'R151-dsn-diagnostic/native_copy' / x['path']) == x['sha256']

payloads = []
def preserve(src, rel):
    data = src.read_bytes()
    compressed = src.suffix == '.kicad_pcb' or len(data) > 524288
    dest = out / rel
    if compressed:
        dest = dest.with_name(dest.name + '.gz')
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert not dest.exists()
    dest.write_bytes(gzip.compress(data, mtime=0) if compressed else data)
    payloads.append(dict(path=dest.relative_to(out).as_posix(), sha256=sha(dest),
                         source_sha256=hashlib.sha256(data).hexdigest(),
                         source_bytes=len(data), gzip=compressed))

trials = []
projects = {'R151A', 'R151B', 'R151C', 'R151D', 'R151F'}
for p in sorted(b.glob('R151*')):
    if p.is_file():
        preserve(p, Path('raw') / p.name)
    elif p.name in projects:
        preserve(p / board, Path('boards') / (p.name + '.kicad_pcb'))
        row = dict(revision=p.name, board_sha256=sha(p / board), adopted=False)
        d = read(b / (p.name + '-drc.json'))
        row.update({k:len(d.get(k, [])) for k in ['unconnected_items', 'violations', 'schematic_parity']})
        row['native_violation_descriptions'] = [x['description'] for x in d['violations']]
        a = read(b / (p.name + '-audit.json'))
        row.update(
            power_width_failures=[dict(net=x['net'], width_mm=x['width_mm'], lost_pair_count=len(x['lost_pairs'])) for x in a['power_width'] if x['status'] == 'FAIL'],
            lost_pad_connections=[dict(net=x['net'], lost_pair_count=len(x['lost_pad_pairs'])) for x in a['lost_pad_connections']],
            retained_reference_losses=a['retained_trace_reference_loss'],
            new_reference_gap_count=sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] > 1e-6 for x in a['new_copper_review']),
            ground_groups=len(a['GND_groups']), ground_pad_count=sum(len(x) for x in a['GND_groups']),
            critical_placement_failures=sum(x['status'] == 'FAIL' for x in a['critical_placement']),
            reference_transition_failures=sum(x['status'] == 'FAIL' for x in a['reference_transitions']))
        trials.append(row)
    else:
        for q in sorted(p.rglob('*')):
            # This copy is byte-verified by the audit/manifest and is identical
            # to the accepted native input; do not duplicate all 78 members.
            if 'native_copy' not in q.relative_to(p).parts and q.is_file():
                preserve(q, Path('raw') / q.relative_to(b))
assert not (b / 'R151E-plan.json').exists()
assert not (b / 'R151E' / board).exists()
trials.append(dict(revision='R151E', adopted=False,
                   build_status='PREPARATION_REJECTED_BEFORE_PLAN_OR_BOARD',
                   reason='Straightened F.Cu filter escape failed geometry screening; the attempted build then rejected the missing plan. Both reports retained.'))
preserve(Path(__file__), Path('archive_R151_study.py'))

def write(name, data):
    (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')

write('summary.json', dict(
    scope=__doc__, accepted_revision='R148E', accepted_board_sha256=expected,
    accepted_remaining_connections=26, remaining_connectivity_fraction=.65,
    not_engineering_progress=True, adopted_trials=[], candidates=trials,
    source_non_pcb_members_unchanged=77,
    full_candidate_six_layer_review='NOT_TESTED', erc_in_this_study='NOT_RUN',
    useful_local_result='The explicit 0.50 mm In2 HEAD_VM bridge restored the two width regressions in F, but F is rejected for CAM/MOTION_3V3 continuity and native violations.',
    search_limit='Fixed-geometry raster failures do not establish global infeasibility. The F input already has power splits.',
    diagnostic_tool_failure='R140_width_restore.py assumes all width anchors are vias; it stopped on a pad anchor. R151 region-based diagnostics support both types and did not alter acceptance checks.',
    dsn_transport_qualification='FAIL_INCOMPLETE_RULE_TRANSPORT',
    autorouting_run=False, ses_import_run=False, new_runtime_installation=False,
    remote_main_observed='aa94dddebcc8ca40cc4b63616147f81448ef087f',
    manufacturing_release=False, goal_complete=False))
write('archive_manifest.json', dict(scope=__doc__, payloads=payloads))
for row in payloads:
    p = out / row['path']
    assert sha(p) == row['sha256']
    data = gzip.decompress(p.read_bytes()) if row['gzip'] else p.read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['source_sha256']
assert sha(source / board) == expected
write('archive_verification.json', dict(
    status='PASS', payload_count=len(payloads), stored_and_original_bytes_verified=True,
    accepted_board_unchanged=True, source_non_pcb_members_unchanged=77,
    diagnostic_native_copy_unchanged=True, all_local_trials_preserved=True))
print(json.dumps(dict(status='PASS', archive_payloads=len(payloads), accepted_revision='R148E', remaining=26, goal_complete=False)))
