#!/usr/bin/env python3
"""Offline publication checks. Never imports or enables robot control."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ('README.md', 'ASSEMBLY.md', 'STATUS.md', 'DELIVERY.md',
        'mechanical/README.md', 'hardware/README.md', 'hardware/WIRING.md',
        'control/README.md', 'evidence/README.md')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()


def relative_path(base, name):
    p = PurePosixPath(name)
    require(bool(name) and not p.is_absolute() and '..' not in p.parts
            and '\\' not in name, f'Unsafe relative path: {name}')
    target = base.joinpath(*p.parts)
    require(target.resolve().is_relative_to(base.resolve()), f'Escaping path: {name}')
    return target


def check_imports():
    manifest = json.loads((ROOT / 'import_manifest.json').read_text())
    seen = set()
    for row in manifest['entries']:
        name = row['path']
        require(name not in seen, f'Duplicate import: {name}')
        seen.add(name)
        p = relative_path(ROOT, name)
        require(p.is_file() and not p.is_symlink(), f'Not a regular artifact: {name}')
        require(p.stat().st_size == row['bytes'], f'Size changed: {name}')
        with p.open('rb') as f:
            require(digest(f) == row['sha256'], f'Hash changed: {name}')
        if 'members' in row:
            expected = {member['path']: member for member in row['members']}
            require(len(expected) == len(row['members']), f'Duplicate manifest member: {name}')
            with zipfile.ZipFile(p) as archive:
                infos = archive.infolist()
                require(len(infos) == len(expected) and
                        {i.filename for i in infos} == set(expected), f'ZIP member set: {name}')
                for info in infos:
                    relative_path(ROOT, info.filename)  # Validate only; never extract.
                    require(not info.is_dir() and (info.external_attr >> 16) & 0o170000 != 0o120000,
                            f'ZIP non-file: {info.filename}')
                    member = expected[info.filename]
                    require(info.file_size == member['bytes'], f'ZIP size: {info.filename}')
                    with archive.open(info) as f:
                        require(digest(f) == member['sha256'], f'ZIP hash: {info.filename}')
    source = ROOT / 'control'
    hashes = json.loads((source / 'source_manifest.json').read_text())['sha256']
    project = json.loads((ROOT / 'project.json').read_text())
    require(project['software_revision'] == 'v184', 'Unexpected control revision')
    require(len(hashes) == project['source_file_count'], 'Unexpected control source count')
    with (source / 'source_manifest.json').open('rb') as f:
        require(digest(f) == project['source_manifest_sha256'], 'Control manifest differs from project version')
    for name, expected in hashes.items():
        with relative_path(source, name).open('rb') as f:
            require(digest(f) == expected, f'Control source hash: {name}')
    return len(seen), len(hashes)


def check_stl(path):
    """Check binary STL topology after welding coordinates at 1e-6 mm."""
    data = path.read_bytes()
    require(len(data) >= 84, f'STL header: {path.name}')
    count = struct.unpack_from('<I', data, 80)[0]
    require(count > 0 and len(data) == 84 + 50 * count, f'STL length: {path.name}')
    vertices, edges, parents = {}, {}, []
    low, high = [math.inf] * 3, [-math.inf] * 3
    volume = 0.0

    def root(v):
        while parents[v] != v:
            parents[v] = parents[parents[v]]
            v = parents[v]
        return v

    for offset in range(84, len(data), 50):
        values = struct.unpack_from('<12fH', data, offset)
        coords = [tuple(values[i:i + 3]) for i in (3, 6, 9)]
        require(all(math.isfinite(v) for c in coords for v in c), f'Non-finite STL: {path.name}')
        ids = []
        for c in coords:
            key = tuple(round(v, 6) for v in c)
            if key not in vertices:
                vertices[key] = len(parents)
                parents.append(len(parents))
            ids.append(vertices[key])
            for axis, value in enumerate(c):
                low[axis] = min(low[axis], value)
                high[axis] = max(high[axis], value)
        require(len(set(ids)) == 3, f'Collapsed triangle: {path.name}')
        a, b, c = coords
        volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) +
                   a[1] * (b[2] * c[0] - b[0] * c[2]) +
                   a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
        for i, j in ((ids[0], ids[1]), (ids[1], ids[2]), (ids[2], ids[0])):
            key = (min(i, j), max(i, j))
            n, orientation = edges.get(key, (0, 0))
            edges[key] = (n + 1, orientation + (1 if i < j else -1))
            ri, rj = root(i), root(j)
            if ri != rj:
                parents[ri] = rj
    bad = sum(n != 2 or orientation != 0 for n, orientation in edges.values())
    components = len({root(i) for i in range(len(parents))})
    require(bad == 0, f'Open/nonmanifold/inconsistent STL edges: {path.name}: {bad}')
    require(components == 1 and volume > 0, f'STL connectivity/volume: {path.name}')
    return dict(file=path.name, triangles=count, vertices=len(vertices), components=components,
                bad_edges=bad, volume_mm3=volume, bounds_mm=[low, high])


def check_links():
    checked = 0
    for name in DOCS:
        doc = ROOT / name
        for target in re.findall(r'!?\[[^\]]*\]\(([^\s)]+)\)', doc.read_text()):
            url = urlsplit(target.strip('<>'))
            if url.scheme or url.netloc or not url.path:
                continue
            require(not url.path.startswith('/'), f'Nonportable local link: {name}: {target}')
            resolved = (doc.parent / unquote(url.path)).resolve()
            require(resolved.is_relative_to(ROOT) and resolved.exists(), f'Broken local link: {name}: {target}')
            checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Optional NEW JSON result file')
    args = parser.parse_args()
    imports, control = check_imports()
    stls = sorted((ROOT / 'mechanical/print').glob('*.stl'))
    require(len(stls) == 5, 'Expected exactly five curated STL files')
    report = dict(status='PASS', imported_artifacts=imports, control_source_files=control,
                  links=check_links(), meshes=[check_stl(p) for p in stls],
                  scope='Integrity and digital topology only; no hardware I/O or physical qualification')
    if args.output:
        with args.output.open('x') as f:
            json.dump(report, f, indent=2)
            f.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
