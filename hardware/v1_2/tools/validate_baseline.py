#!/usr/bin/env python3
"""Validate migration evidence and prevent accidental use of obsolete wiring."""
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'hardware/v1_2'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []

    def check(name, ok, detail):
        checks.append({'name': name, 'status': 'PASS' if ok else 'FAIL', 'detail': detail})

    archive = ROOT / 'hardware/revisions/pre_V1_2_20260922'
    manifest = read(archive / 'manifest.json')
    for entry in manifest['files']:
        if 'path' in entry:
            check('archive ' + entry['path'], sha(archive / entry['path']) == entry['sha256'], 'Original snapshot hash')
        else:
            check('exact import ' + entry['imported_path'], sha(ROOT / entry['imported_path']) == entry['sha256'], 'User document preserved byte-for-byte')
    cat = read(ROOT / 'contracts/components.json')
    electric = read(ROOT / 'contracts/electrical_interfaces.json')
    baseline = read(ROOT / 'config/project_baseline.json')
    check('revision agreement', cat['revision'] == electric['revision'] == baseline['hardware_revision'], cat['revision'])
    check('four actuators', sum(p['quantity'] for p in cat['components'] if p['category'] == 'actuator') == 4, 'Two wheel + two head')
    check('two application MCUs', sum(p['quantity'] for p in cat['components'] if p['category'] == 'controller') == 2, 'CAM auxiliary expander separately recorded')
    for name in ['bom', 'pinmap', 'harness']:
        with (ROOT / 'hardware' / f'{name}.csv').open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        check(name + ' version', bool(rows) and all(r['revision'] == cat['revision'] for r in rows), str(len(rows)) + ' rows')
    check('unknown prices not zero', all(p['unit_price_cny'] is None or p['unit_price_cny'] > 0 for p in cat['components']), 'Null in JSON / UNKNOWN in CSV')
    budget = read(HERE / 'reports/budget_gate.json')
    check('incomplete budget not passed', not budget['unknown_price_ids'] or (budget['status'] == 'BLOCKED' and budget['full_landed_total_cny'] is None), 'Unknown prices cannot imply <=1000')
    check('no release', not electric['pcb_release'] and not electric['procurement_release'] and not cat['manufacturing_release'], 'PROTOTYPE_UNVALIDATED')
    motion = [r for r in electric['pinmap'] if r['domain'] == 'motion']
    check('P1 motion pin assignment', bool(motion) and all(r['mcu_pin'] and r['assignment_status'] == 'P1_SCHEMATIC_ASSIGNED_NOT_BENCH_VERIFIED' for r in motion) and len({r['mcu_pin'] for r in motion})==len(motion), 'Native F412 candidate; no old ESP32 pins copied')
    check('18-pin FFC coverage', [r['pin'] for r in electric['display_ffc']['pin_number_review']] == list(range(1, 19)), 'Document mapping; no cable release')
    check('no false TE claim', electric['display_ffc']['TE_available_at_cam'] is False, 'CAM L3 pin10 NC')
    wire = read(HERE / 'reports/interface_calculations.json')
    check('baud arithmetic', wire['official_reference']['brr_decimal'] == 17 and wire['candidate_not_implemented']['brr_decimal'] == 16, 'HOST calculation only')
    check('software frame reused', '#define MORI_WIRE_MAX 158' in (ROOT / 'contracts/wire.h').read_text() and electric['bus_interfaces']['motion_interaction']['frame_max_bytes'] == 158, 'Existing software files; no protocol rewrite')
    protected = [ROOT / 'contracts/components.json', ROOT / 'contracts/electrical_interfaces.json', ROOT / 'hardware/v1/bom_candidates.json']
    before_guard = {str(p): sha(p) for p in protected}
    guard = subprocess.run([sys.executable, str(ROOT / 'hardware/v1/tools/publish_display_motor_review.py')], capture_output=True, text=True, timeout=20)
    check('historical publisher refused', guard.returncode != 0 and 'REFUSED' in (guard.stdout + guard.stderr), (guard.stdout + guard.stderr).strip())
    check('guard had no output mutations', all(sha(Path(p)) == h for p, h in before_guard.items()), 'Active contracts and historical BOM unchanged')
    preserved = read(HERE / 'reports/preserved_before_hardware_publish.json')['files']
    observed = [{'path': p, 'unchanged_since_hardware_publish_start': sha(ROOT / p) == h,
                 'before_sha256': h, 'current_sha256': sha(ROOT / p)} for p, h in preserved.items()]
    # Another user-owned task can update shared geometry concurrently: report it,
    # never restore our snapshot or claim an external change was a hardware edit.
    result = {
        'revision': cat['revision'], 'run_utc': datetime.now(timezone.utc).isoformat(),
        'evidence_layer': 'HOST_TEST',
        'status': 'PASS' if all(c['status'] == 'PASS' for c in checks) else 'FAIL',
        'checks': checks, 'shared_file_observations': observed,
        'shared_file_policy': 'Hardware publisher does not write these files; changed hashes can reflect concurrent owner work.',
        'BENCH': 'NOT_TESTED', 'ROBOT': 'NOT_TESTED', 'ERC': 'See cad_validation.json', 'DRC': 'See cad_validation.json'
    }
    (HERE / 'reports/migration_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'{result["status"]}: {len(checks)} migration checks; '
          f'{sum(not o["unchanged_since_hardware_publish_start"] for o in observed)} shared files changed externally since snapshot.')
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
