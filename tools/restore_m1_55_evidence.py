"""Restore a selected M1.55 local evidence package without overwriting work."""
import argparse
import json
from pathlib import Path
import restore_archive_assets as archive


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
    selected = {}
    for name in args.group:
        if name not in groups:
            parser.error('Unknown group: '+name)
        group = groups[name]
        bundle = archive.destination(archive.DEFAULT_ROOT, group['archive'])
        if not bundle.is_file() or archive.digest(bundle) != group['sha256']:
            parser.error('Missing/changed package: '+group['archive'])
        for entry in group['files']:
            if entry['archive'] != group['archive'] or entry['archive_sha256'] != group['sha256']:
                parser.error('Inconsistent package member: '+entry['path'])
            if entry['path'] in selected:
                previous = selected[entry['path']]
                if (previous['bytes'], previous['sha256']) != (entry['bytes'], entry['sha256']):
                    parser.error('Conflicting package member: '+entry['path'])
                continue
            selected[entry['path']] = entry
    # Check every destination before writing any member.
    for name, entry in selected.items():
        target = archive.destination(args.root, name)
        if target.exists() and (not target.is_file() or target.stat().st_size != entry['bytes']
                                or archive.digest(target) != entry['sha256']):
            parser.error('Existing file differs; no extraction started: '+name)
    for name, entry in selected.items():
        print(archive.restore(args.root, entry), name, flush=True)


if __name__ == '__main__':
    main()
