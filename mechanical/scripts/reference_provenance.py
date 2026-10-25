"""Portable historical evidence checks, separate from current geometry checks."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluated_dock_reference(project, path, preserved_main_sha256):
    """Use the published, pinned matrix receipt; never read an author's home path."""
    project = Path(project).resolve()
    path = Path(path).resolve()
    relative = path.relative_to(project).as_posix()
    manifest = json.loads((project/'mechanical/input_assets/m1_58_manifest.json').read_text())
    rows = [row for row in manifest['files'] if row['path'] == relative]
    if len(rows) != 1 or sha(path) != rows[0]['sha256']:
        raise ValueError('Evaluated dock receipt is not the published input: '+relative)
    dock = json.loads(path.read_text())
    if dock['preserved_main_sha256'] != preserved_main_sha256:
        raise ValueError('Evaluated dock receipt belongs to a different main model')
    provenance = dict(status='BLOCKED', recorded_source=dock['source_file'],
        expected_sha256=dock['source_file_sha256'], matrix_receipt=relative,
        matrix_receipt_sha256=rows[0]['sha256'],
        reason='Original comparison Blender source is not published; only the pinned evaluated matrices are checked.')
    source = Path(dock['source_file'])
    if not source.is_absolute():
        source = (project/source).resolve()
        if not source.is_relative_to(project):
            raise ValueError('Dock source path escapes the project')
        if source.is_file():
            if sha(source) != dock['source_file_sha256']:
                raise ValueError('Dock source hash mismatch')
            provenance.update(status='PASS', reason='Repository-relative original comparison source hash verified.')
    return dock, provenance


def historical_hardware_provenance(project, expected):
    """A retired owner snapshot is not the current driver's source-preservation test.

    Missing/different files remain visible as BLOCKED. Do not download retired
    designs into current paths or call their absence a geometry modification.
    """
    project = Path(project).resolve()
    missing, different = [], []
    for name, digest in expected.items():
        path = (project/name).resolve()
        if not path.is_relative_to(project):
            raise ValueError('Historical hardware path escapes the project')
        if not path.is_file():
            missing.append(name)
        elif sha(path) != digest:
            different.append(name)
    return dict(status='BLOCKED' if missing or different else 'PASS',
        recorded_files=len(expected), matching_files=len(expected)-len(missing)-len(different),
        missing_files=missing, different_files=different,
        scope='Historical adoption receipt only. Current published driver integrity is checked by tools/check_project.py; no electrical fit or preservation qualification is inferred.')
