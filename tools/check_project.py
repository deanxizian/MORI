#!/usr/bin/env python3
"""Offline publication integrity, separate from engineering qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ENTRY_DOCS = (
    'README.md', 'docs/PROJECT_LAYOUT.md', 'docs/PROJECT_INDEX.md',
    'docs/REQUIREMENTS.md', 'docs/CHANGELOG.md', 'docs/GITHUB_ARCHIVE.md',
    'docs/CURRENT_STATUS.md', 'docs/PREARRIVAL_BLOCKERS.md', 'mechanical/README.md', 'mechanical/LATEST_MODEL.md',
    'mechanical/studies/README.md', 'hardware/README.md',
    'hardware/driver/README.md', 'hardware/driver/harness/README.md',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(root, allow_lfs_pointers=False):
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    baseline = json.loads((root/'config/project_baseline.json').read_text())
    assets = json.loads((root/'docs/current_assets.json').read_text())
    package = json.loads((root/'package.json').read_text())
    require(baseline['project_version'] == package['version'] == assets['project_version'], 'Project version differs')
    require(baseline['mechanical_revision'] == json.loads((root/'config/geometry.json').read_text())['revision'], 'Mechanical revision differs')
    require(not baseline['manufacturing_release'], 'Prototype publication must not imply manufacturing release')
    require(not baseline['animation_matches_main_model'], 'Old animation must be labeled separately')
    for name in ('MORI_SPEC_V1.md', 'README_SOFTWARE_V1.md', 'README_SOFTWARE_V1_2.md'):
        require(not (root/name).exists(), 'Obsolete duplicate entry: '+name)
    for entry in assets['assets']:
        path = root/entry['path']
        if not path.is_file():
            errors.append('Missing asset: '+entry['path'])
            continue
        data = path.read_bytes()
        if data.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
            expected = f"oid sha256:{entry['sha256']}\nsize {entry['bytes']}\n".encode()
            require(allow_lfs_pointers and entry['storage'] == 'GIT_LFS' and expected in data, 'LFS bytes missing or wrong pointer: '+entry['path'])
        else:
            require(len(data) == entry['bytes'] and digest(data) == entry['sha256'], 'Asset changed: '+entry['path'])
    native = json.loads((root/'hardware/driver/manifest.json').read_text())
    bundle = root/native['bundle']['path']
    require(digest(bundle.read_bytes()) == native['bundle']['sha256'], 'Native bundle hash mismatch')
    with zipfile.ZipFile(bundle) as z:
        expected = {f['path']: f for f in native['files']}
        require(set(z.namelist()) == set(expected) and len(z.namelist()) == len(expected), 'Native bundle member set differs')
        require(z.testzip() is None, 'Native bundle CRC failure')
        for name, row in expected.items():
            data = z.read(name)
            require(len(data) == row['bytes'] and digest(data) == row['sha256'], 'Native member differs: '+name)
        require(digest(z.read('MORI_Interface_C3.kicad_pcb')) == native['source_board_sha256'], 'Native PCB source bytes changed')
        for table in ['fp-lib-table', 'sym-lib-table']:
            require(b'/Users/' not in z.read(table), 'Non-portable library table')
    status = json.loads((root/'hardware/driver/status.json').read_text())
    require(status['board_sha256'] == native['source_board_sha256'], 'PCB status from a different source')
    require(status['status'] == 'FAIL' and not status['manufacturing_release'], 'Unrouted PCB mislabeled')
    renders = json.loads((root/'mechanical/reports/off_shelf_render_manifest.json').read_text())
    model = next(e for e in assets['assets'] if e['path'] == 'mechanical/mori_v1_2.blend')
    require(renders['source_blend_sha256'] == model['sha256'], 'Views from a different model')
    for row in renders['views']:
        require(digest((root/'mechanical'/row['file']).read_bytes()) == row['sha256'], 'Render bytes differ: '+row['file'])
    source = json.loads((root/'mechanical/input_assets/m1_58_manifest.json').read_text())
    require(digest((root/source['archive']).read_bytes()) == source['sha256'], 'Build-input bundle changed')
    with zipfile.ZipFile(root/source['archive']) as z:
        require(z.testzip() is None, 'Build-input ZIP CRC failure')
        for row in source['files']:
            require(digest(z.read(row['member'])) == row['sha256'], 'Build input differs: '+row['path'])
    # Check actual tracked paths, so ignored local files cannot conceal broken GitHub links.
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0'))
    for name in ENTRY_DOCS:
        text = (root/name).read_text()
        links = re.findall(r'\[[^\]]*\]\(([^)]+)\)', text)
        for url in links:
            u = urlsplit(url.strip('<>'))
            if u.scheme or u.netloc or not u.path:
                continue
            path = ((root/name).parent/unquote(u.path)).resolve()
            try:
                relative = path.relative_to(root.resolve()).as_posix()
            except ValueError:
                errors.append(f'{name}: link outside repository: {url}')
                continue
            require(relative in tracked or any(p.startswith(relative.rstrip('/')+'/') for p in tracked), f'{name}: unpublished link {url}')
    require('renders/ups_controls_M1_58/assembled.png' in (root/'README.md').read_text(), 'Missing shelled README image')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-lfs-pointers', action='store_true', help='CI metadata check; does not claim LFS payload availability')
    args = parser.parse_args()
    errors = check(ROOT, args.allow_lfs_pointers)
    print(json.dumps({'status': 'FAIL' if errors else 'PASS', 'scope': 'Publication integrity only', 'lfs_mode': 'pointers allowed' if args.allow_lfs_pointers else 'actual bytes', 'errors': errors}, ensure_ascii=False, indent=2))
    return bool(errors)

if __name__ == '__main__':
    sys.exit(main())
