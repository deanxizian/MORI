#!/usr/bin/env python3
"""Build V1.2 tables from hardware-owned canonical contracts; no hardware I/O."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / 'hardware/v1_2'


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def table(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: 'UNKNOWN' if v is None else
                json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                for k, v in row.items()})


def main():
    baseline = read(ROOT / 'config/project_baseline.json')
    cat = read(ROOT / 'contracts/components.json')
    electric = read(ROOT / 'contracts/electrical_interfaces.json')
    rev = cat['revision']
    if baseline['hardware_revision'] != rev or electric['revision'] != rev:
        raise SystemExit('REFUSED: active baseline and contracts do not match')
    parts = cat['components']
    assert sum(p['quantity'] for p in parts if p['category'] == 'actuator') == 4
    assert sum(p['quantity'] for p in parts if p['category'] == 'controller') == 2
    assert all(p['unit_price_cny'] is None or p['unit_price_cny'] > 0 for p in parts)
    sources = {s['id']: s for s in read(HERE / 'sources/index.json')['sources']}
    bom = []
    for part in parts:
        row = {'revision': rev, **part}
        row['source_urls'] = [sources[s]['url'] for s in part['source_ids'] if sources[s]['url']]
        row['source_local_paths'] = [sources[s]['local_path'] for s in part['source_ids'] if sources[s]['local_path']]
        row['subtotal_cny'] = None if part['unit_price_cny'] is None else part['quantity'] * part['unit_price_cny']
        bom.append(row)
    for path in [HERE / 'bom.csv', HERE / f'bom_{rev}.csv', ROOT / 'hardware/bom.csv']:
        table(path, bom)
    for name, rows in [('pinmap', electric['pinmap']), ('harness', electric['harness'])]:
        table(HERE / 'interfaces' / f'{name}_{rev}.csv', rows)
        table(ROOT / 'hardware' / f'{name}.csv', rows)
    # The legacy root filename remains a projection, never a second pin truth.
    table(ROOT / 'hardware/wiring.csv', electric['harness'])
    table(HERE / 'interfaces/display_ffc_review.csv', electric['display_ffc']['pin_number_review'])
    table(HERE / 'interfaces/component_envelopes.csv', [{
        'revision': rev, 'id': p['id'], 'model': p['full_model'], 'quantity': p['quantity'],
        'vendor_dimensions_mm': p['dimensions_mm'], 'vendor_mass_g': p['mass_g'],
        'data_status': p['data_status'], 'shaft_hole_interface': p['shaft_hole_interface'],
        'connector_clearance_mm': p['connector_clearance_mm'],
        'mechanical_keys': p['mechanical_contract_keys'],
        'allocation_source': 'contracts/mechanical_interfaces.json (not vendor dimensions)',
        'missing': p['missing'], 'mounting_release': p['mounting_release']
    } for p in parts])
    unknown = [p['id'] for p in parts if p['unit_price_cny'] is None]
    unqualified = [p['id'] for p in parts if p['unit_price_cny'] is not None
                   and p.get('price_status') != 'CONFIRMED_EXACT_SKU']
    known_quote_subtotal = sum(p['quantity'] * p['unit_price_cny'] for p in parts if p['unit_price_cny'] is not None)
    total = None if unknown or unqualified else sum(p['quantity'] * p['unit_price_cny'] for p in parts)
    cap = cat['budget']['hard_cap_cny']
    budget = {
        'revision': rev, 'hard_cap_cny': cap,
        'planning_target_cny': cat['budget']['planning_target_cny'],
        'reserve_cny': cat['budget']['reserve_cny'],
        'required_lines': len(parts),
        'published_model_quote_lines': len(parts) - len(unknown),
        'exact_quoted_lines': len(parts) - len(unknown) - len(unqualified),
        'model_quotes_pending_variant_confirmation': unqualified,
        'published_model_quote_subtotal_cny': known_quote_subtotal if len(parts) > len(unknown) else None,
        'unknown_price_ids': unknown, 'full_landed_total_cny': total,
        'over_cap_cny': None if total is None else max(total - cap, 0),
        'remaining_cap_cny': None if total is None else cap - total,
        'status': 'BLOCKED' if total is None else 'PASS' if total <= cap else 'FAIL',
        'note': 'Published model prices and qualified exact-variant prices are separate. Neither incomplete subtotal nor a mismatched display lead proves full <=1000 compliance.',
        'quote_leads': cat['quote_leads'], 'physical_tests': 'NOT_TESTED'
    }
    write(HERE / 'reports/budget_gate.json', budget)
    # Snapshot vendor file hashes without rewriting their content or provenance.
    evidence = []
    for source in sources.values():
        local = source['local_path']
        if local and (ROOT / local).is_file():
            evidence.append({'id': source['id'], 'path': local,
                             'sha256': hashlib.sha256((ROOT / local).read_bytes()).hexdigest()})
    write(HERE / 'reports/source_file_hashes.json', {'revision': rev, 'files': evidence})
    print(f'{rev}: {len(parts)} BOM rows; {len(electric["pinmap"])} pin rows; '
          f'{len(electric["harness"])} harness rows; budget {budget["status"]}')


if __name__ == '__main__':
    main()
