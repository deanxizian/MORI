"""Receive mechanical static-harness evidence without selecting new wire.

Read-only checks of mechanical results and existing hardware source hashes.
Does not rerun or claim an independent geometry simulation.
"""
from pathlib import Path
import csv
import hashlib
import itertools
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SRC = ROOT / 'mechanical/studies/prearrival_finish/harness_A2'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n')


def run():
    assert not (HERE / 'receipt.json').exists(), 'Preserve an existing receipt; use a new directory.'
    snapshots = HERE / 'snapshots'; snapshots.mkdir(exist_ok=True)
    manifests = []
    for name in ['ecowire_validation.json', 'ecowire_joint.json', 'ecowire_candidate.json', 'ecowire_sources.json']:
        source = SRC / name; data = source.read_bytes()
        target = snapshots / name; target.write_bytes(data)
        manifests.append(dict(source=source.relative_to(ROOT).as_posix(),
                              snapshot=target.relative_to(ROOT).as_posix(), sha256=sha(target)))
    val = json.loads((snapshots/'ecowire_validation.json').read_text())
    joint = json.loads((snapshots/'ecowire_joint.json').read_text())
    cand = json.loads((snapshots/'ecowire_candidate.json').read_text())
    source = json.loads((snapshots/'ecowire_sources.json').read_text())
    expected = {f'H{h:02}_{p}' for h in range(1,4) for p in [1,2]}
    expected_pairs = {tuple(sorted(pair)) for pair in itertools.combinations(expected, 2)}
    actual_pairs = {tuple(sorted([row['a'],row['b']])) for row in val['wire_to_wire']}
    a3p = ROOT / 'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A3_J10.json'
    a3 = json.loads(a3p.read_text())
    checks = dict(
        six_wire_ids={r['id'] for r in val['rigid_solids']} == expected,
        six_single_connected_solids=all(r['positive_connected_components']==1 and not r['overlaps'] and r['status']=='PASS' for r in val['rigid_solids']),
        complete_15_unique_pairs=len(val['wire_to_wire'])==15 and actual_pairs==expected_pairs,
        pair_reports_no_overlap=all(r['intersection_mm3']==0 and r['status']=='PASS' for r in val['wire_to_wire']),
        reported_130_poses_no_overlap=val['head_motion']['poses']==130 and not val['head_motion']['overlaps'],
        joint_hash_matches=sha(snapshots/'ecowire_joint.json')==val['source_joint_sha256'],
        candidate_hash_matches=sha(snapshots/'ecowire_candidate.json')==joint['source_sha256'],
        model_hash_matches=sha(ROOT/'mechanical/mori_v1_2.blend')==val['source_blend_sha256']==joint['source_blend_sha256'],
        mechanical_input_hashes_match=all(sha(ROOT/p)==h for p,h in cand['sources'].items()),
        formal_native_boards_match=all(sha(ROOT/q['file'])==q['sha256'] for q in cand['native_board_sources'].values()),
        all_16_formal_files_unchanged=all(sha(ROOT/p)==h for p,h in a3['native_source_manifest'].items()),
        wire_source_hashes_match=all(sha(ROOT/q['source_file'])==q['source_sha256'] for q in source['products']),
        cut_lengths_not_released=val['cut_lengths_released'] is False,
        geometry_change_false=val['geometry_change'] is False,
    )
    with (ROOT/'hardware/v1_2/prearrival_20261002/harness_detail.csv').open(encoding='utf-8-sig') as file:
        harness_rows = [r for r in csv.DictReader(file) if r['线束'] in ['H01','H02','H03']]
    checks['three_expected_hardware_harness_ids'] = {r['线束'] for r in harness_rows}=={'H01','H02','H03'}
    result = dict(id='MECHANICAL_H01_H03_STATIC_RECEIPT_20261002', date='2026-10-02',
        status='PASS' if all(checks.values()) else 'FAIL',
        check_scope='Receipt integrity, result consistency and source identity only; geometry result received from mechanical, not independently rerun.',
        received_revision=val['revision'], source_thread_id='01a0c226-811d-75d2-8f93-350cad266a22',
        checks=checks, source_manifest=manifests,
        reported_nominal_geometry_status=val['status'],
        min_nominal_tessellated_surface_gap_mm=min(r['nominal_tessellated_solid_gap_mm'] for r in val['wire_to_wire']),
        reported_head_poses=val['head_motion']['poses'],
        formal_harness_rows_unchanged=harness_rows,
        proposed_wire_by_harness={'H01':'Alpha EcoWire6712 AWG24','H02':'Alpha EcoWire6711 AWG26','H03':'Alpha EcoWire6711 AWG26'},
        selection_status='BLOCKED', adopted_in_formal_BOM=False, current_pinmap_changed=False,
        electrical_current_voltage_drop_and_crimp_qualification='NOT_TESTED',
        complete_harness_status='BLOCKED', J10_eight_wire_status='BLOCKED',
        limits=val['limits'], A3_sha256=sha(a3p),
        formal_boards_modified=False, mechanical_model_modified=False,
        procurement_release=False, manufacturing_release=False, physical_tests='NOT_TESTED')
    dump(HERE/'receipt.json',result)
    print(json.dumps({'status':result['status'],'checks':checks,'min_gap_mm':result['min_nominal_tessellated_surface_gap_mm']},ensure_ascii=False,indent=2))
    assert all(checks.values()), 'Inspect receipt.json; source/result mismatch.'


if __name__ == '__main__':
    run()
