"""Restore a selected M1.55 local evidence package without overwriting work."""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile
import restore_archive_assets as archive


def checked_destination(root, name):
    target = archive.destination(root, name)
    if target == root:
        raise ValueError('Expected a file below the destination root: '+name)
    # exists() on a leaf is false when an ancestor is a regular file. Check
    # every ancestor explicitly, including a not-yet-created destination root.
    inside_root = True
    for parent in target.parents:
        if parent.exists() and not parent.is_dir():
            raise ValueError('Non-directory ancestor; no extraction started: '+str(parent))
        if parent == root:
            inside_root = False
        if inside_root and parent.is_symlink():
            raise ValueError('Symlink ancestor; no extraction started: '+str(parent))
    return target


def restore_groups(manifest, names, root, source_root):
    """Preflight the whole selection, then stream from one open ZIP per bundle."""
    root = Path(root).absolute()
    selected = {}
    with ExitStack() as stack:
        bundles = {}
        for name in names:
            if name not in manifest['groups']:
                raise ValueError('Unknown group: '+name)
            group = manifest['groups'][name]
            key = group['archive']
            if key not in bundles:
                bundle = archive.destination(source_root, key)
                if not bundle.is_file() or archive.digest(bundle) != group['sha256']:
                    raise ValueError('Missing/changed package: '+key)
                bundles[key] = (group['sha256'], stack.enter_context(zipfile.ZipFile(bundle)))
            if bundles[key][0] != group['sha256']:
                raise ValueError('Conflicting package hash: '+key)
            for entry in group['files']:
                if (entry['storage'] != 'LOCAL_ZIP' or entry['archive'] != key
                        or entry['archive_sha256'] != group['sha256']):
                    raise ValueError('Inconsistent package member: '+entry['path'])
                path = str(Path(entry['path']))
                if path in selected:
                    previous = selected[path]
                    if (previous['bytes'], previous['sha256']) != (entry['bytes'], entry['sha256']):
                        raise ValueError('Conflicting package member: '+path)
                    continue
                selected[path] = entry
        destinations = {name: checked_destination(root, name) for name in selected}
        targets = set(destinations.values())
        for name, target in destinations.items():
            entry = selected[name]
            if any(parent in targets for parent in target.parents):
                raise ValueError('Selected file is also a destination directory: '+name)
            if target.exists() and (not target.is_file() or target.stat().st_size != entry['bytes']
                                    or archive.digest(target) != entry['sha256']):
                raise ValueError('Existing file differs; no extraction started: '+name)
            info = bundles[entry['archive']][1].getinfo(entry['member'])
            if info.is_dir() or info.file_size != entry['bytes']:
                raise ValueError('Invalid member size/type: '+name)
        results = []
        for name, entry in selected.items():
            target = checked_destination(root, name)
            if target.exists():
                # Recheck to preserve a file changed after the initial preflight.
                if target.stat().st_size != entry['bytes'] or archive.digest(target) != entry['sha256']:
                    raise FileExistsError('Existing file changed; retained unchanged: '+name)
                results.append(('already present', name))
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            checked_destination(root, name)
            temp = None
            try:
                h = hashlib.sha256()
                total = 0
                with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.mori-evidence-', delete=False) as output:
                    temp = Path(output.name)
                    with bundles[entry['archive']][1].open(entry['member']) as source:
                        for block in iter(lambda: source.read(1024 * 1024), b''):
                            total += len(block)
                            if total > entry['bytes']:
                                raise ValueError('Member exceeds recorded size: '+name)
                            h.update(block)
                            output.write(block)
                if total != entry['bytes'] or h.hexdigest() != entry['sha256']:
                    raise ValueError('Member SHA256 or size mismatch: '+name)
                # Exclusive publication never replaces a file created meanwhile.
                os.link(temp, target)
                results.append(('restored', name))
            finally:
                if temp is not None:
                    temp.unlink(missing_ok=True)
        return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--group', action='append', default=[])
    parser.add_argument('--root', type=Path, default=archive.DEFAULT_ROOT)
    args = parser.parse_args()
    manifest = json.loads((archive.DEFAULT_ROOT/'docs/review_evidence/M1_55_archives.json').read_text())
    if manifest['revision'] != 'V1.2-M1.55':
        parser.error('Unexpected evidence revision')
    groups = manifest['groups']
    if args.list or not args.group:
        for name, group in groups.items():
            print(f"{name}: {len(group['files'])} files; {group['scope']}")
        return
    try:
        results = restore_groups(manifest, args.group, args.root, archive.DEFAULT_ROOT)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    for result, name in results:
        print(result, name, flush=True)


if __name__ == '__main__':
    main()
