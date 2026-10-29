"""Read-only publication review of frozen MORI development evidence.

This checks source preservation, declared archive hashes and local links. It is
not a circuit, manufacturing or physical qualification checker.
"""
import ast
import collections
import gzip
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

root = Path.cwd()
dev = root / 'robot/hardware/driver/development'
out = Path(sys.argv[1])
errors = []
counts = collections.Counter()
digest = lambda data: hashlib.sha256(data).hexdigest()
status = json.loads((dev / 'STATUS.json').read_text())
assert status['revision'] == 'C3 R188C'
assert status['board_sha256'] == digest((dev / 'native/MORI_Interface_C3.kicad_pcb').read_bytes())
assert status['manufacturing_release'] is False and status['goal_complete'] is False
bundle = dev.parent / 'MORI_Driver_C3_R108P.zip'
with zipfile.ZipFile(bundle) as z:
    for name in z.namelist():
        if name.endswith('.kicad_pcb'):
            continue
        if (dev / 'native' / name).read_bytes() != z.read(name):
            errors.append('Changed source member: ' + name)
        counts['original_non_PCB_members_checked'] += 1
assert counts['original_non_PCB_members_checked'] == 77

for manifest in sorted((dev / 'evidence').rglob('archive_manifest.json')):
    data = json.loads(manifest.read_text())
    entries = data.get('payloads', data.get('files'))
    if isinstance(entries, dict):
        entries = [dict(path=k, sha256=v) for k, v in entries.items()]
    if not isinstance(entries, list):
        errors.append('Unsupported archive schema: ' + str(manifest))
        continue
    for row in entries:
        name = row.get('path', row.get('stored_file', row.get('archive')))
        expected = row.get('stored_sha256', row.get('archive_sha256', row.get('sha256')))
        if not name or not isinstance(expected, str):
            errors.append('Unsupported archive row: ' + str(manifest))
            continue
        p = manifest.parent / name
        if manifest.parent.name == 'R145_study':
            # This historical manifest explicitly uses the evidence root, including R145I.
            p = manifest.parent.parent / name
        elif not p.exists() and name.startswith(manifest.parent.name + '/'):
            p = manifest.parent.parent / name
        try:
            p.resolve().relative_to(dev)
            raw = p.read_bytes()
            assert digest(raw) == expected
            decoded = gzip.decompress(raw) if p.suffix == '.gz' else raw
            if row.get('source_sha256'):
                assert digest(decoded) == row['source_sha256']
            counts['declared_archive_payloads_checked'] += 1
        except (OSError, ValueError, AssertionError, EOFError) as exc:
            errors.append(str(p.relative_to(root)) + ': ' + type(exc).__name__)
    for name, expected in data.get('source_non_PCB_members', {}).items():
        if digest((dev / 'native' / name).read_bytes()) != expected:
            errors.append('Source member reconstruction mismatch: ' + str(manifest) + '/' + name)
        counts['omitted_source_member_hashes_checked'] += 1
    counts['archive_manifests_checked'] += 1

secret_patterns = [re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),
                   re.compile(rb'github_pat_[A-Za-z0-9_]{40,}'),
                   re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
for p in sorted(dev.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts or '/publication_20261029/' in p.as_posix():
        continue
    raw = p.read_bytes()
    if p.suffix == '.gz':
        try:
            raw = gzip.decompress(raw)
            counts['gzip_payloads_decoded'] += 1
        except (OSError, EOFError) as exc:
            errors.append('Bad gzip: ' + str(p.relative_to(root)))
            continue
    if any(pattern.search(raw) for pattern in secret_patterns):
        errors.append('Credential-pattern match: ' + str(p.relative_to(root)))
    suffix = p.with_suffix('').suffix if p.suffix == '.gz' else p.suffix
    if suffix == '.json':
        try:
            json.loads(raw)
            counts['json_payloads_parsed'] += 1
        except (ValueError, UnicodeError):
            errors.append('Invalid JSON: ' + str(p.relative_to(root)))
    if p.parent == dev / 'scripts' and p.suffix == '.py':
        ast.parse(raw)
        counts['active_Python_scripts_parsed'] += 1

tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], text=True).split('\0'))
for p in [dev / 'README.md', dev / 'NEXT.md', *(dev / 'evidence').glob('*/README.md')]:
    for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', p.read_text()):
        u = urlsplit(link.strip('<>'))
        if u.scheme or u.netloc or not u.path:
            continue
        target = (p.parent / unquote(u.path)).resolve()
        try:
            rel = target.relative_to(root).as_posix()
        except ValueError:
            errors.append('Link outside repository: ' + str(p) + ': ' + link)
            continue
        if rel not in tracked and not any(x.startswith(rel.rstrip('/') + '/') for x in tracked):
            errors.append('Unpublished link: ' + str(p.relative_to(root)) + ': ' + link)
        counts['local_markdown_links_checked'] += 1

result = dict(status='FAIL' if errors else 'PASS', scope=__doc__, counts=dict(counts), errors=errors,
              current_board_sha256=status['board_sha256'], engineering_status='FAIL',
              manufacturing_release=False, physical='NOT_TESTED')
with out.open('x') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(bool(errors))
