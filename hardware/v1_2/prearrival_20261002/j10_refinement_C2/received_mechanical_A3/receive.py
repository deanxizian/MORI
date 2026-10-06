"""Archive the mechanical A3 reply and verify its input/result consistency.

No native board, handed-off A3, mechanical file or component selection changes.
"""
from pathlib import Path
import collections
import hashlib
import itertools
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = ROOT / 'mechanical/studies/prearrival_finish/J10_A3_review/review.json'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    assert not (HERE/'receipt.json').exists(), 'Do not overwrite an existing receipt.'
    raw = SOURCE.read_bytes(); report = json.loads(raw)
    script = ROOT/'mechanical/studies/prearrival_finish/review_J10_A3.py'
    (HERE/'review.json').write_bytes(raw)
    (HERE/'review_J10_A3.py.source.txt').write_bytes(script.read_bytes())
    rows = report['local_eight_wire_bends']
    expected_pairs = {tuple(pair) for pair in itertools.combinations(range(1,9),2)}
    valid_passes = all(
        len(r['pins'])==8 and all(p['status']=='PASS' for p in r['pins'])
        and len(r['wire_to_wire'])==28
        and {(g['a'],g['b']) for g in r['wire_to_wire']}==expected_pairs
        and min(g['surface_clearance_lower_bound_mm'] for g in r['wire_to_wire'])>=.3
        for r in rows if r['status']=='PASS')
    checks = dict(
        all_recorded_input_hashes_match=all(sha(ROOT/p)==h for p,h in report['sources'].items()),
        model_hash_matches=sha(ROOT/'mechanical/mori_v1_2.blend')==report['source_blend_sha256'],
        report_remains_blocked=report['status']=='BLOCKED' and not report['manufacturing_release'],
        actual_exit_height_unknown=report['actual_terminal_exit_height_mm'] is None,
        expected_backside_parts={r['reference'] for r in report['backside']}=={'D30','F70','R50'},
        backside_reports_no_overlap=all(not r['actual_overlaps'] for r in report['backside']),
        plug_box_paths_no_overlap=all(not r['overlaps'] for r in report['continuous_swept_boxes']),
        all_90_wire_scenarios_present=len(rows)==90,
        all_scenarios_keep_5mm_straight=all(r['terminal_straight_allocation_mm']==5 for r in rows),
        reported_passes_include_complete_eight_wire_pair_check=valid_passes,
        PH18_blocker_preserved=report['formal_PH_hole_issue']['affected_connectors']==18 and report['formal_PH_hole_issue']['status']=='FAIL',
        source_reports_main_unchanged=report['main_unchanged'] is True,
    )
    summary = []
    for wire in sorted({r['wire'] for r in rows}):
        for z in sorted({r['assumed_exit_z_above_pcb_mm'] for r in rows if r['wire']==wire}):
            cases=[r for r in rows if r['wire']==wire and r['assumed_exit_z_above_pcb_mm']==z]
            summary.append(dict(wire=wire,ASSUMED_exit_height_mm=z,
                                passing_local_angles_from_Y_deg=[r['bend_angle_from_Y_deg'] for r in cases if r['status']=='PASS']))
    operations = []
    for r in report['straight_operating_allocations']:
        blocked=[v['object'] for v in r['overlaps']]
        operations.append(dict(target=r['target'], diameter_allocation_mm=r['diameter_allocation_mm'],
                               installed_obstructions=blocked,
                               obstructions_remaining_without_yaw_base_and_bearing=[n for n in blocked if n not in ['Yaw_Base','Yaw_Bearing']],
                               scope='Unselected straight cylindrical approach only; not cap grasp or probe contact qualification.'))
    output=dict(id='MECHANICAL_A3_J10_RECEIPT_20261002', date='2026-10-02',
        receipt_status='PASS' if all(checks.values()) else 'FAIL',
        receipt_scope='Input hashes and reported result consistency; mechanical geometry was not independently rerun by this receipt.',
        design_status='BLOCKED', checks=checks,
        source=SOURCE.relative_to(ROOT).as_posix(), source_sha256=sha(SOURCE),
        script_source=script.relative_to(ROOT).as_posix(), script_sha256=sha(script),
        backside=report['backside'], local_bend_sensitivity=summary, operation_summary=operations,
        JP70_function='Short C5_EN to GND to disable U70/+5V_CAM; not a motor emergency-stop interface.',
        TP71_function='GND test pad; access after installing yaw support is not qualified.',
        decision='Retain candidate only. Backside local envelopes may inform next design; complete wiring and maintenance access still blocked.',
        remaining_work=['Actual mated terminal/wire exit height and dimensions',
                        'Selected jumper cap and service/probe approach, including assembly sequence',
                        'Entire H05 plus other harnesses, strain relief and cable-attached removal',
                        'C2 routing closure, PH18 finished-hole remediation, thermal and electrical checks'],
        physical_tests='NOT_TESTED', procurement_release=False, manufacturing_release=False,
        formal_boards_changed=False, mechanical_model_changed=False,
        limits=report['limitations'])
    (HERE/'receipt.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'receipt_status':output['receipt_status'],'checks':checks,'bend_sensitivity':summary},ensure_ascii=False,indent=2))
    assert all(checks.values()), 'Review receipt.json before accepting the result.'


if __name__=='__main__':
    run()
