#!/usr/bin/env python3
"""Audit published S3 interfaces against KiCad's physical netlist and prior IO.

Run with the bundled Python (pypdf). Does not alter CAD, contracts or mechanics.
"""
from datetime import datetime, timezone
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pypdf import PdfReader
from logic5v_S3 import H, DEST, REPORT, NAME, REV

R = H.parents[1]
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def serialized(value):
    if value is None:
        return 'UNKNOWN'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def main():
    cat = read(R / 'contracts/components.json')
    e = read(R / 'contracts/electrical_interfaces.json')
    old = read(H / 'revisions/before_logic5V_S3_20260922/electrical_interfaces.json')
    base = read(R / 'config/project_baseline.json')
    native = read(REPORT / 'verification.json')
    parts = {p['id']: p for p in cat['components']}
    original = [{k: v for k, v in p.items() if k != 'revision'} for p in old['pinmap']]
    inherited = [{k: v for k, v in p.items() if k != 'revision'} for p in e['pinmap'][:len(original)]]
    actual = {}
    for n in ET.parse(REPORT / 'netlist.xml').getroot().findall('.//nets/net'):
        for node in n.findall('node'):
            actual[node.attrib['ref'], node.attrib['pin']] = n.attrib['name'].lstrip('/')
    added = e['pinmap'][len(original):]
    new_pin_errors = [p for p in added if actual.get((p['connector'].split('.')[-1], str(p['pin_number']))) != p['net']]
    checks = {
        'baseline_and_contract_revisions_match': base['hardware_revision'] == cat['revision'] == e['revision'] == REV,
        'original_59_IO_assignments_unchanged': len(original) == 59 and original == inherited,
        '12_added_power_pins_match_native_netlist': len(added) == 12 and not new_pin_errors,
        'four_actuators_two_application_MCUs_retained':
            sum(p['quantity'] for p in parts.values() if p['category'] == 'actuator') == 4
            and sum(p['quantity'] for p in parts.values() if p['category'] == 'controller') == 2,
        'no_duplicate_external_5V_module_purchase': parts['logic_power']['full_model'] == 'TPS54302DDCR'
            and parts['logic_power']['quantity'] == 2 and not any('D24V22F5' in p['full_model'] for p in parts.values()),
        'no_frozen_power_outline_or_release': parts['carrier_pcb']['dimensions_mm']['power_xy'] is None
            and not e['hardware_freeze'] and not e['pcb_release'] and not cat['manufacturing_release'],
        'power_schematic_and_PCB_mismatch_explicit': not e['pcb_revision_relationship']['synchronized']
            and not list(DEST.glob('*.kicad_pcb')),
        'S3_harness_has_no_inherited_position_claim': all('UNFROZEN' in h['view_direction'] for h in e['harness'] if h['from_'].startswith(NAME+'.')),
        'current_native_checks_match_schematic': native['status'] == 'PASS'
            and native['schematic_sha256'] == sha(DEST / (NAME+'.kicad_sch')),
    }
    for name, expected in [('pinmap', e['pinmap']), ('harness', e['harness'])]:
        table = rows(R / 'hardware' / (name+'.csv'))
        checks[name+'_CSV_matches_contract'] = len(table) == len(expected) and all(
            all(row.get(k) == serialized(v) for k, v in item.items()) for row, item in zip(table, expected))
        checks[name+'_versioned_CSV_matches_current'] = (H / 'interfaces' / (name+'_'+REV+'.csv')).read_bytes() == (R / 'hardware' / (name+'.csv')).read_bytes()
    bom = rows(R / 'hardware/bom.csv')
    checks['BOM_CSV_matches_contract'] = len(bom) == len(parts) and all(
        all(row.get(k) == serialized(v) for k, v in parts[row['id']].items()) for row in bom)
    checks['BOM_versions_and_wiring_alias_match'] = (H / 'bom.csv').read_bytes() == (H / ('bom_'+REV+'.csv')).read_bytes() == (R / 'hardware/bom.csv').read_bytes() and (R / 'hardware/wiring.csv').read_bytes() == (R / 'hardware/harness.csv').read_bytes()
    assembly = {r['ref']: r for r in rows(DEST / 'assembly_bom.csv')}
    checks['branch_assembly_MPNs_and_J6_DNP_match'] = all(assembly[ref]['mpn'] == mpn for ref, mpn in {
        'U60':'TPS54302DDCR', 'U70':'TPS54302DDCR', 'F60':'0451001.MRL', 'F70':'0451002.MRL',
        'L60':'SRP7050TA-100M', 'L70':'SRP7050TA-100M'}.items()) and assembly['J6']['dnp'] == 'True'
    preserved = read(H / 'revisions/before_logic5V_S3_20260922/preserve_hashes.json')
    checks['all_existing_P2_native_CAD_unchanged'] = all(sha(R / p) == digest for p, digest in preserved.items() if '/kicad/' in p)
    evidence = read(H / 'reports/source_file_hashes.json')
    checks['recorded_local_evidence_hashes_match'] = all((R / x['path']).is_file() and sha(R / x['path']) == x['sha256'] for x in evidence['files'])
    checks['all_active_schematic_paths_exist'] = all((R / p).is_file() for p in e['active_schematics'].values())
    pdf = H / 'schematic_S3/previews/MORI_S3_Power_Schematic_Review.pdf'
    reader = PdfReader(pdf)
    checks['PDF_has_12_pages_and_was_exported_after_schematic'] = len(reader.pages) == 12 and pdf.stat().st_mtime >= (DEST / (NAME+'.kicad_sch')).stat().st_mtime
    checks['PDF_every_page_marks_PCB_not_updated'] = all('PCB NOT UPDATED' in p.extract_text() for p in reader.pages)
    result = dict(revision=REV, utc=datetime.now(timezone.utc).isoformat(),
        status='PASS' if all(checks.values()) else 'FAIL',
        scope='Published interfaces and artifacts only; no electrical bench or PCB qualification.',
        counts=dict(main_BOM=len(bom), pinmap=len(e['pinmap']), connector_endpoint_rows=len(e['harness']), PDF_pages=len(reader.pages)),
        checks={k:'PASS' if v else 'FAIL' for k,v in checks.items()}, new_pin_errors=new_pin_errors,
        schematic_sha256=sha(DEST / (NAME+'.kicad_sch')), PDF_sha256=sha(pdf),
        contract_sha256={p:sha(R / p) for p in ['contracts/components.json','contracts/electrical_interfaces.json']},
        physical_tests='NOT_TESTED')
    (REPORT / 'interface_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(result['status'], len(checks), 'interface/artifact checks')
    if not all(checks.values()):
        print({k:v for k,v in result['checks'].items() if v == 'FAIL'})
        raise SystemExit(1)


if __name__ == '__main__':
    main()
