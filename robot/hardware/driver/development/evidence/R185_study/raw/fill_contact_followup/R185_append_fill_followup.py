"""Append fill-contact correction; preserve every original R185 raw payload."""
import gzip
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

b = Path('robot/.state/c3-completion/trials')
dev = Path('robot/hardware/driver/development')
study = dev / 'evidence/R185_study'
dest = study / 'raw/fill_contact_followup'
assert not dest.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
manifest = read(study / 'archive_manifest.json')
old_payloads = list(manifest['payloads'])
assert len(old_payloads) == 203
assert all(sha(study / row['path']) == row['sha256'] for row in old_payloads)
controls = read(b / 'R185-filled-ground-controls.json')
audit = read(b / 'R185I-audit-v2.json')
delta = read(b / 'R185I-planned-delta-v2.json')
assert controls['status'] == delta['status'] == 'PASS' and len(controls['checks']) == 5
assert len(delta['checks']) == 2508 and not delta['errors']
assert audit['reference_ground_anchor_count'] == 126
expected = '13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert read(study / 'summary.json')['source_sha256'] == expected
assert sha(dev / 'native/MORI_Interface_C3.kicad_pcb') == expected
assert all(sha(dev / 'native' / name) == value for name, value in manifest['source_non_PCB_members'].items())
dest.mkdir()

def preserve(path, name=None):
    raw = path.read_bytes()
    target = dest / (name or path.name)
    with target.open('xb') as f:
        f.write(raw)
    manifest['payloads'].append(dict(path=target.relative_to(study).as_posix(), sha256=sha(target),
                                    source_sha256=hashlib.sha256(raw).hexdigest(), source_bytes=len(raw), gzip=False))

for name in ['archive_manifest.json', 'archive_verification.json', 'summary.json', 'corrections.json']:
    preserve(study / name, 'before_' + name)
for name in ['copper_geometry.py', 'audit_candidate.py', 'plan_layered_route.py', 'review_planned_delta.py']:
    preserve(dev / 'scripts' / name)
for name in ['R185_filled_ground_controls.py', 'R185-filled-ground-controls.json',
             'R185I-audit-v2.json', 'R185I-planned-delta-v2.json',
             'R185-filled-ground-followup-commands.json', 'R185_append_fill_followup.py']:
    preserve(b / name)

review = dict(recorded_at_utc=datetime.now(timezone.utc).isoformat(), status='PASS',
              source_sha256=expected, candidate_sha256=audit['board_sha256'],
              correction='Previous ground-anchor tests intersected the land with full copper including itself. They now require positive-area contact with actual In1/In4 GND zone fill only.',
              corrected_consumers=['audit_candidate', 'plan_layered_route', 'review_planned_delta'],
              retained_older_reports='Original raw/helpers and I/J geometry reports remain byte-identical. Their actual_plane_contacts used a full-copper proxy, not independent actual-zone evidence. Do not use those contact areas as fill-only measurements.',
              new_actual_fill_checks=controls['checks'], candidate_planned_delta_checks=len(delta['checks']),
              reference_transition_results_unchanged=True, accepted_transition_flags=6, candidate_transition_flags=5,
              native_DRC_ERC='Existing source-bound results retained; no PCB geometry or saved bytes changed by this correction.',
              adopted=False, manufacturing_release=False, physical='NOT_TESTED')
review_source = b / 'R185-filled-ground-review.json'
with review_source.open('x') as f:
    json.dump(review, f, indent=2, ensure_ascii=False); f.write('\n')
preserve(review_source)

def write(name, value):
    (study / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')

summary = read(study / 'summary.json')
summary['actual_ground_fill_followup'] = dict(evidence='raw/fill_contact_followup/R185-filled-ground-review.json',
    status='PASS', controls=5, candidate_planned_delta_checks=2508, accepted_counts_unchanged=True,
    method=audit['reference_ground_anchor_method'])
write('summary.json', summary)
corrections = read(study / 'corrections.json')
corrections['items'].append(review['correction'] + ' Both R181C and R185I have 126 eligible anchors and all 114 GND vias attached to both fills. All prior transition distances/statuses remain unchanged; three orphaned-fill controls are rejected. Older raw evidence is preserved.')
write('corrections.json', corrections)
manifest['fill_contact_followup'] = dict(original_payload_count=203, original_payloads_unchanged=True,
                                        evidence=summary['actual_ground_fill_followup']['evidence'])
write('archive_manifest.json', manifest)
for row in manifest['payloads']:
    data = (study / row['path']).read_bytes()
    assert hashlib.sha256(data).hexdigest() == row['sha256']
    raw = gzip.decompress(data) if row['gzip'] else data
    assert len(raw) == row['source_bytes'] and hashlib.sha256(raw).hexdigest() == row['source_sha256']
assert manifest['payloads'][:203] == old_payloads
verification = read(study / 'archive_verification.json')
verification.update(payload_count=len(manifest['payloads']), original_203_payloads_unchanged=True,
                    actual_ground_fill_controls=5, actual_fill_candidate_planned_checks=2508)
write('archive_verification.json', verification)
status = read(dev / 'STATUS.json')
status['reference_ground_contact_review'] = 'evidence/R185_study/raw/fill_contact_followup/R185-filled-ground-review.json'
(dev / 'STATUS.json').write_text(json.dumps(status, indent=2, ensure_ascii=False) + '\n')
print(json.dumps(dict(status='PASS', payloads=len(manifest['payloads']), original_payloads_unchanged=203,
                     canonical_sha256=expected, accepted_revision='R181C', adopted=False)))
