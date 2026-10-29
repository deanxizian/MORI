"""Adopt only the verified PCB into the independent development directory.

Keep source backup, UI state and every non-PCB source member. This is a scoped
development checkpoint with explicit remaining layout work, never a release.
"""
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

dev = Path('robot/hardware/driver/development').resolve()
base = Path('robot/.state/c3-completion').resolve()
source = dev/'native'
candidate = base/'trials/R142'
evidence = dev/'evidence/R142'
backup = base/'baseline_R134N_before_R142'
board_name = 'MORI_Interface_C3.kicad_pcb'
old_sha = '0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
new_sha = '2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def write_json(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
        f.write('\n')

assert sha(source/board_name) == old_sha
assert sha(candidate/board_name) == new_sha
assert not backup.exists()
assert not (evidence/'adoption.json').exists()
result = json.loads((evidence/'result.json').read_text())
assert (result['board_sha256'], result['unconnected_items'], result['violations'],
        result['schematic_parity'], result['erc_violations']) == (new_sha, 29, 0, 0, 0)
planned = json.loads((evidence/'planned-delta.json').read_text())
assert planned['status'] == 'PASS' and len(planned['checks']) == 2622 and not planned['errors']
for name in ['step-regression.json', 'original-baseline-regression.json']:
    a = json.loads((evidence/name).read_text())
    assert a['board_sha256'] == new_sha
    assert not a['lost_pad_connections'] and not a['retained_trace_reference_loss']
    assert len(a['power_width']) == 50 and all(x['status'] == 'PASS' for x in a['power_width'])
    assert len(a['critical_placement']) == 63 and all(x['status'] == 'PASS' for x in a['critical_placement'])
    assert [len(g) for g in a['GND_groups']] == [155]
    assert all(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] < 1e-7 for x in a['new_copper_review'])
    assert sum(x['status'] == 'FAIL' for x in a['reference_transitions']) == 6

members = sorted(p.relative_to(base/'baseline') for p in (base/'baseline').rglob('*')
                 if p.is_file() and p.name not in [board_name, 'MORI_Interface_C3.kicad_prl'])
assert len(members) == 77
member_records = []
for rel in members:
    assert (source/rel).read_bytes() == (candidate/rel).read_bytes() == (base/'baseline'/rel).read_bytes(), str(rel)
    member_records.append({'member': str(rel), 'sha256': sha(source/rel)})
all_source = {p.relative_to(source).as_posix(): sha(p) for p in source.rglob('*') if p.is_file()}
extras = {rel: digest for rel, digest in all_source.items()
          if rel not in {str(p) for p in members} and rel != board_name}
old_status = (dev/'STATUS.json').read_bytes()
assert json.loads(old_status)['board_sha256'] == old_sha
shutil.copytree(source, backup, copy_function=shutil.copy2)
assert {p.relative_to(backup).as_posix(): sha(p) for p in backup.rglob('*') if p.is_file()} == all_source

shutil.copy2(candidate/board_name, source/board_name)
assert sha(source/board_name) == new_sha
for rel, digest in all_source.items():
    if rel != board_name:
        assert sha(source/rel) == digest, rel
assert (dev/'STATUS.json').read_bytes() == old_status

adopted = datetime.now(timezone.utc).isoformat()
write_json(evidence/'adoption.json', {
    'adopted_at_utc': adopted, 'source_sha256': old_sha, 'adopted_board_sha256': new_sha,
    'source_commit': 'ffe54eb5f51508f823b4e9a3165a9045f9b7e0f4',
    'source_full_local_backup': str(backup), 'other_native_members_unchanged': 77,
    'member_checks': member_records, 'extra_local_ui_state_preserved': extras,
    'development_only': True, 'published_revision': 'C3 R108P',
    'adopted_in_main_model': False, 'adopted_in_software': False,
    'remaining_style_work': ['ADC upper small offsets', 'FAULT In2 small offset', 'C1403 ground bridge', 'whole-board per-track/per-via/six-layer review'],
    'engineering_status': 'FAIL', 'physical': 'NOT_TESTED', 'manufacturing_release': False,
    'goal_complete': False})
views = json.loads((evidence/'views/image_manifest.json').read_text())
viewed_names = {'F.Cu-native.svg', 'B.Cu-native.svg', 'B-ADC-upper.svg', 'B-ADC-lower.svg',
                'B-R301-CLR.svg', 'B-R903-before.svg', 'B-R903-after.svg',
                'In3-OUT-CAM.svg', 'In2-FAULT.svg'}
body = json.loads((evidence/'body-review.json').read_text())
assert not body['same_face_projections']
write_json(evidence/'visual_review.json', {
    'source_sha256': old_sha, 'candidate_sha256': new_sha,
    'scope': 'Seven diagnostic PNGs and native front/back overview PNGs actually inspected. No complete six-layer/per-track/per-via review claimed.',
    'images': [{**row, 'actually_viewed_as_PNG': row['file'] in viewed_names} for row in views['images']],
    'new_same_face_nominal_body_screen': 'PASS', 'new_same_face_projection_count': 0,
    'body_limits': body['outline_limits'], 'opposite_or_internal_projection_groups': len(body['opposite_or_internal_projections']),
    'new_and_retained_reference_screen': 'PASS',
    'local_route_smoothness': 'FAIL',
    'local_route_smoothness_explanation': 'ADC upper 0.10 mm offsets, FAULT In2 0.10 mm offset and C1403 bridge retained as explicit unfinished optimization work. Failed fixed-layout alternatives do not justify global optimality or waive the preference.',
    'whole_board_visual': 'NOT_TESTED', 'coupling': 'NOT_TESTED', 'thermal': 'NOT_TESTED',
    'physical': 'NOT_TESTED', 'manufacturing_release': False})
drc = json.loads((evidence/'drc.json').read_text())
with (evidence/'remaining_connections.csv').open('x', newline='') as f:
    w = csv.writer(f)
    w.writerow(['item', 'description', 'endpoint_descriptions'])
    for n, item in enumerate(drc['unconnected_items'], 1):
        w.writerow([n, item['description'], ' | '.join(x['description'] for x in item['items'])])
status = dict(result)
status.update({
    'revision': 'C3 R142', 'status': 'INDEPENDENT_DEVELOPMENT_CANDIDATE',
    'published_revision': 'C3 R108P', 'adopted_in_main_model': False,
    'previous_candidate': 'C3 R134N', 'previous_candidate_sha256': old_sha,
    'strict_regression_explanation': 'Raw R108P and R134N step audits retain FAIL for explicitly planned component/pad/owned guard changes and 32 replaced source tracks. Exact-plan review passes 2622 checks; electrical/reference regressions pass. Local route-smoothness and whole-board review are unfinished.',
    'step_regression_status': 'FAIL', 'planned_delta_review_status': 'PASS',
    'electrical_regression_status': 'PASS', 'local_visual_review': 'FAIL',
    'local_visual_review_explanation': 'Scoped static inspection completed; small local offsets remain for group-layout optimization. No blanket style or whole-board PASS.',
    'new_same_face_nominal_body_projection_groups': 0,
    'remaining_FAULT_N_groups': 4, 'remaining_ARMED_groups': 3,
    'remaining_HEAD_VM_groups': 1, 'remaining_U401_2Y_groups': 1,
    'remaining_ACT_CURRENT_ADC_groups': 1, 'remaining_U1001_D3_groups': 1,
    'segment_count': 1258, 'via_count': 322, 'footprint_count': 215,
    'baseline_unconnected_items': 40, 'remaining_connectivity_fraction': .725,
    'connectivity_fraction_is_not_engineering_progress': True,
    'goal_complete': False})
(dev/'STATUS.json').write_text(json.dumps(status, indent=2)+'\n')
print(json.dumps({'development_revision': 'C3 R142', 'unconnected_items': 29,
                  'other_DRC': 0, 'original_non_PCB_members_unchanged': 77,
                  'backup': str(backup), 'goal_complete': False}))
