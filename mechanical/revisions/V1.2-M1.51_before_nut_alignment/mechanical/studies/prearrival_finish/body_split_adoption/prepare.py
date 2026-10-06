"""Preserve M1.50 before the user-approved front/rear shell adoption."""
from pathlib import Path
import datetime, hashlib, json, shutil

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[3]
SNAP = PROJECT / 'mechanical/revisions/V1.2-M1.50_before_body_split'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
assert not (OUT / 'preparation.json').exists(), 'Do not overwrite a recorded baseline'
delivery = read(OUT.parent / 'cam_entry_adoption/delivery.json')
assert delivery['revision'] == 'V1.2-M1.50' and delivery['status'] == 'PASS'
assert sha(PROJECT / 'mechanical/mori_v1_2.blend') == delivery['source_blend_sha256']
protected = read(OUT.parent / 'cam_entry_adoption/preparation.json')['protected_hardware']
for name, h in protected.items():
    assert sha(PROJECT / name) == h, name
paths = {PROJECT / name for name in delivery['files']}
paths |= {PROJECT / 'AGENTS.md', PROJECT / 'config/geometry.json',
          PROJECT / 'contracts/mechanical_interfaces.json', OUT.parent / 'work_status.json',
          OUT.parent / 'goal_block_audit.json'}
for folder in ['mechanical/scripts', 'mechanical/reports', 'mechanical/renders',
               'mechanical/animation', 'mechanical/exports']:
    paths |= {p for p in (PROJECT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
files = {}
for p in sorted(paths):
    rel = p.relative_to(PROJECT)
    q = SNAP / rel
    q.parent.mkdir(parents=True, exist_ok=True)
    if q.exists():
        assert sha(q) == sha(p), rel
    else:
        shutil.copy2(p, q)
    assert sha(q) == sha(p), rel
    files[str(rel)] = {'snapshot': str(q.relative_to(PROJECT)), 'sha256': sha(p)}
candidate = OUT.parent / 'head_harness_M1_49/remaining_routes/cam_restraints/body_front_rear_split'
approval = {
    'date': '2026-10-06', 'user_text': '采纳你的建议',
    'context_url': 'http://127.0.0.1:58201/mechanical/studies/prearrival_finish/head_harness_M1_49/remaining_routes/cam_restraints/body_front_rear_split/index.html',
    'scope': 'Adopt the displayed two-piece front/rear body-shell direction, four underside diameter6.6 tool ports, original four frame fastener sites, and retirement of four horizontal-seam screws/inserts; complete seam locating and wiring/assembly studies within that direction.',
    'not_authorized': ['supplier contact', 'C6 adoption', 'sliding-guide v4 adoption', 'return-clamp v3 adoption', 'hardware PCB edits', 'manufacturing release'],
    'candidate_files': {str(p.relative_to(PROJECT)): sha(p) for p in candidate.iterdir() if p.is_file()},
}
(OUT / 'approval.json').write_text(json.dumps(approval, ensure_ascii=False, indent=2) + '\n')
result = dict(status='PASS', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              revision='V1.2-M1.50', source_blend_sha256=delivery['source_blend_sha256'],
              snapshot_root=str(SNAP.relative_to(PROJECT)), files=files, protected_hardware=protected)
(OUT / 'preparation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print('BODY_SPLIT_BASELINE_SAVED', len(files), 'files;', len(protected), 'hardware files preserved')
