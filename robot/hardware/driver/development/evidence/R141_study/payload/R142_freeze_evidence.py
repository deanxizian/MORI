"""Freeze R141 studies and the checked R142 development candidate.

Original reports are copied byte-for-byte (optionally lossless gzip). No native
board is changed here. Replaying historical builders needs their pinned source
boards and new output directories; this is not a manufacturing release.
"""
import copy
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

base = Path('robot/.state/c3-completion/trials').resolve()
dev = Path('robot/hardware/driver/development').resolve()
original = Path('robot/.state/c3-completion/baseline').resolve()
source_sha = '0d25f5871d7e5521a07b75ab1cd8662a8492fd97d1d19b7fb98a95a22ba1e2ca'
candidate_sha = '2a7c04b8430875a0f8f9e4bdde4b789da6b8efb5f84ee991a360f1d5b6d006dd'
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha((dev/'native/MORI_Interface_C3.kicad_pcb').read_bytes()) == source_sha
assert sha((base/'R142/MORI_Interface_C3.kicad_pcb').read_bytes()) == candidate_sha
assert not (dev/'evidence/R141_study').exists()
assert not (dev/'evidence/R142').exists()

def write_json(path, obj):
    with path.open('x') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write('\n')

members = sorted(p.relative_to(original) for p in original.rglob('*')
                 if p.is_file() and p.name not in
                 ['MORI_Interface_C3.kicad_pcb', 'MORI_Interface_C3.kicad_prl'])
assert len(members) == 77
expected_pro = json.loads((original/'MORI_Interface_C3.kicad_pro').read_text())
normalized_pro = copy.deepcopy(expected_pro)
for item in normalized_pro['board']['design_settings']['teardrop_parameters']:
    item.setdefault('td_enabled', False)
for key in ['net_colors', 'netclass_assignments']:
    if normalized_pro['net_settings'][key] is None:
        normalized_pro['net_settings'][key] = {}
metadata = []
for rev in ['R141B', 'R141C', 'R141E', 'R141F', 'R141G', 'R141H', 'R141I', 'R142']:
    unchanged, normalizations = [], []
    for rel in members:
        a, b = (original/rel).read_bytes(), (base/rev/rel).read_bytes()
        if a == b:
            unchanged.append({'member': str(rel), 'sha256': sha(a)})
        else:
            assert rel.name == 'MORI_Interface_C3.kicad_pro', (rev, str(rel))
            assert json.loads(b) == normalized_pro, rev
            normalizations.append({'member': str(rel), 'original_sha256': sha(a),
                                   'normalized_sha256': sha(b),
                                   'meaning': 'Only three known default-value classes; no rule/severity changes. Trial bytes preserved.'})
    assert len(unchanged) + len(normalizations) == 77
    if rev == 'R142':
        assert len(unchanged) == 77
    metadata.append({'revision': rev, 'unchanged_original_members': unchanged,
                     'known_project_normalizations': normalizations})
write_json(base/'R141-project-member-review.json', {
    'scope': 'Read-only exact original-member and known normalization review. No source/project writes.',
    'original_member_count_excluding_board': 77, 'candidates': metadata})

study = dev/'evidence/R141_study'
study.mkdir()
files = {Path(__file__).resolve(), base/'R138_joint_search.py', base/'run_R138_trial.py',
         base/'R140T-fault-transfer-sites/result.json'}
boards, metrics = [], []
for obj in base.iterdir():
    if not obj.name.startswith('R141'):
        continue
    if obj.is_file():
        files.add(obj)
        continue
    board = obj/'MORI_Interface_C3.kicad_pcb'
    if not board.exists():
        files.update(p for p in obj.rglob('*') if p.is_file())
        continue
    boards.append({'revision': obj.name, 'local_source': str(board),
                   'sha256': sha(board.read_bytes()), 'size_bytes': board.stat().st_size,
                   'included_in_archive': False})
    for name in ['edit_plan.json', 'edit_manifest.json']:
        if (obj/name).exists():
            files.add(obj/name)
    d = json.loads((base/(obj.name+'-drc.json')).read_text())
    a = json.loads((base/(obj.name+'-audit.json')).read_text())
    metrics.append({'revision': obj.name,
        **{k: len(d[k]) for k in ['unconnected_items', 'violations', 'schematic_parity']},
        'lost_pad_nets': [x['net'] for x in a['lost_pad_connections']],
        'power_width_failures': sum(x['status'] != 'PASS' for x in a['power_width']),
        'ground_group_sizes': [len(g) for g in a['GND_groups']],
        'retained_reference_loss_rows': len(a['retained_trace_reference_loss']),
        'new_reference_gap_rows': sum(x['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] > 1e-7 for x in a['new_copper_review']),
        'critical_placement_failures': sum(x['status'] != 'PASS' for x in a['critical_placement']),
        'reference_transition_flags': sum(x['status'] == 'FAIL' for x in a['reference_transitions'])})

def archive_file(source, target, root, compress=False):
    data = source.read_bytes()
    archived = gzip.compress(data, mtime=0) if compress else data
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as f:
        f.write(archived)
    assert (gzip.decompress(target.read_bytes()) if compress else target.read_bytes()) == data
    return {'source': str(source), 'source_sha256': sha(data), 'source_size_bytes': len(data),
            'archive': str(target.relative_to(root)), 'archive_sha256': sha(archived),
            'compression': 'gzip' if compress else 'none'}

records = []
for f in sorted(files):
    rel = f.relative_to(base)
    compress = f.suffix in ['.json', '.log', '.svg'] and f.stat().st_size > 1500
    records.append(archive_file(f, study/('payload/'+str(rel)+('.gz' if compress else '')), study, compress))
write_json(study/'manifest.json', {
    'created_utc': datetime.now(timezone.utc).isoformat(),
    'scope': 'Independent R141 studies, no native study directly adopted. R141I geometry informs the separate fresh R142 reconstruction. Full study projects remain local, not included in the archive. No physical or manufacturing qualification.',
    'canonical_at_study_sha256': source_sha, 'payloads': records,
    'local_native_boards': sorted(boards, key=lambda x: x['revision']),
    'native_trial_summary': sorted(metrics, key=lambda x: x['revision'])})

out = dev/'evidence/R142'
out.mkdir()
accepted_records = []
for f in sorted((base/'R142-verification').iterdir()):
    assert f.is_file()
    target_name = 'step-regression.json' if f.name == 'regression.json' else f.name
    accepted_records.append(archive_file(f, out/target_name, out))
for f in sorted(base.iterdir()):
    if f.is_file() and f.name.startswith('R142') and f.suffix != '.py':
        accepted_records.append(archive_file(f, out/'construction'/f.name, out))
for name in ['R142_consolidate.py', 'R142_build_verify.py', 'R142_views.py',
             'R142_direct_review.py', 'R142_freeze_evidence.py',
             'R141_body_review.py', 'R138_joint_search.py']:
    accepted_records.append(archive_file(base/name, out/'scripts'/name, out))
for name in ['edit_plan.json', 'edit_manifest.json']:
    accepted_records.append(archive_file(base/'R142'/name, out/name, out))
for f in sorted((base/'R142-views').iterdir()):
    assert f.is_file()
    compress = f.suffix == '.svg'
    accepted_records.append(archive_file(f, out/'views'/(f.name+('.gz' if compress else '')), out, compress))
write_json(out/'archive_manifest.json', {
    'created_utc': datetime.now(timezone.utc).isoformat(), 'source_sha256': source_sha,
    'candidate_sha256': candidate_sha,
    'scope': 'Byte-preserved candidate evidence; lossless gzip only for native SVGs. README, adoption, visual scope and repository-check records are separate generated documents.',
    'payloads': accepted_records})
print(json.dumps({'R141_payloads': len(records), 'R141_native_boards': len(boards),
                  'R142_payloads': len(accepted_records), 'R142_original_non_PCB_unchanged': 77}))
