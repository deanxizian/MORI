"""Pack generated DSN/SES without rewriting whitespace or any source bytes.

The first staged whitespace check found native exporter trailing spaces. These
are preserved inside lossless gzip archives, not removed from frozen evidence.
Run once from the repository root after archive_and_adopt_R152.py.
"""
import gzip
import hashlib
import json
from pathlib import Path

root = Path('robot/hardware/driver/development/evidence/R152_study')
trials = Path('robot/.state/c3-completion/trials')
manifest = root / 'archive_manifest.json'
data = json.loads(manifest.read_text())
changes = []
for row in data['payloads']:
    p = root / row['path']
    if p.suffix not in ['.dsn', '.ses']:
        continue
    assert not row['gzip']
    original = p.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    assert digest == row['sha256'] == row['source_sha256']
    local_source = trials / Path(row['path']).relative_to('raw')
    assert local_source.read_bytes() == original
    dest = p.with_name(p.name + '.gz')
    with dest.open('xb') as f:
        f.write(gzip.compress(original, mtime=0))
    assert gzip.decompress(dest.read_bytes()) == original
    changes.append({'previous_path': row['path'], 'gzip_path': dest.relative_to(root).as_posix(),
                    'original_sha256': digest})
    row.update(path=dest.relative_to(root).as_posix(), gzip=True,
               sha256=hashlib.sha256(dest.read_bytes()).hexdigest())
    # This is only the new, unpublished staging copy; the original remains in .state.
    p.unlink()
assert changes
data['exchange_packaging'] = 'DSN/SES compressed losslessly, preserving native exporter whitespace; original local files unchanged.'
manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
for row in data['payloads']:
    stored = (root / row['path']).read_bytes()
    assert hashlib.sha256(stored).hexdigest() == row['sha256']
    raw = gzip.decompress(stored) if row['gzip'] else stored
    assert hashlib.sha256(raw).hexdigest() == row['source_sha256']
with (root / 'exchange_packaging.json').open('x') as f:
    json.dump({'status': 'PASS', 'changes': changes, 'all_payloads_verified': len(data['payloads']),
               'local_sources_unchanged': True, 'reason': __doc__}, f, indent=2)
    f.write('\n')
print(json.dumps({'packed_exchange_files': len(changes), 'verified_payloads': len(data['payloads'])}))
