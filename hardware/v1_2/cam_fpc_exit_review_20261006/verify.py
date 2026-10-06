#!/usr/bin/env python3
"""Read-only input audit. Writes only this evidence package's verification JSON."""
from pathlib import Path
import ast
import hashlib
import json
import platform

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def multiply(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) for row in matrix]


def main():
    protected = json.loads((BASE / 'protected_baseline.json').read_text())['files']
    changed = [p for p, digest in protected.items()
               if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    source = json.loads((BASE / 'source_index.json').read_text())
    source_mismatches = []
    for row in source['reused'] + source['fetched']:
        if 'sha256' in row and sha(BASE / row['file']) != row['sha256']:
            source_mismatches.append(row['file'])

    # Parse, do not execute the mechanical script or its imports.
    tree = ast.parse((BASE / 'inputs/waveshare_detail.py').read_text())
    build = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == 'apply_waveshare_detail')
    assignment = next(n for n in build.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'r' for t in n.targets))
    matrix = ast.literal_eval(assignment.value.args[0])
    expected = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
    vectors = {
        'camera_current_interpreted_mouth': [0, -1, 0],
        'camera_photo_supported_exit': [0, 1, 0],
        'display_current_interpreted_mouth': [1, 0, 0],
        'display_photo_supported_exit': [-1, 0, 0],
    }
    mapped = {key: {'local_UVW': v, 'zero_pose_global_XYZ': multiply(matrix, v)}
              for key, v in vectors.items()}
    handed = json.loads((BASE / 'handoff.json').read_text())
    for port in handed['cam_ports']:
        assert multiply(matrix, port['supported_exit_local_UVW']) == port['supported_exit_zero_pose_XYZ']
    logical = 'hardware/v1_2/wiring_P5R7/06_屏幕FFC待核对.csv'
    logical_copy_equal = sha(ROOT / logical) == sha(BASE / 'inputs/06_屏幕FFC待核对.csv')
    checks = {
        'protected_sources_unchanged': not changed,
        'archived_sources_match': not source_mismatches,
        'zero_pose_matrix_matches_review': matrix == expected,
        'logical_mapping_copy_unchanged': logical_copy_equal,
        'model_changes_applied_false': handed['model_changes_applied'] is False,
    }
    result = {
        'status': 'PASS' if all(checks.values()) else 'FAIL',
        'scope': 'Source integrity and independent zero-pose coordinate arithmetic only; not a fresh geometric or physical fit check',
        'python': platform.python_version(),
        'protected_file_count': len(protected),
        'checks': checks, 'changed_paths': changed,
        'source_mismatches': source_mismatches,
        'cam_board_zero_pose_matrix': matrix, 'directions': mapped,
        'direction_input_basis': 'Code interpretation and human visual inspection recorded in results/visual_review.json; no automated image inference',
        'physical_validation': 'NOT_TESTED', 'manufacturing_release': 'BLOCKED',
    }
    (BASE / 'results/verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'protected_files': len(protected),
                      'changed': changed, 'source_mismatches': source_mismatches}, ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
