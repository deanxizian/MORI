"""Verify the seating receipts and their scope without rerunning Blender."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np

SCRIPT = Path(__file__).resolve()
A8 = SCRIPT.parent
ROOT = A8.parents[3]
TC = A8 / 'cam_wire_forming/lifted_end2/contact_refined_forming'
RS = TC / 'root_seating'
OUT = RS / 'aligned_tails'
read = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
main_hash = sha(ROOT / 'mechanical/mori_v1_2.blend')
paths = [OUT / n for n in ('screen.json', 'math_bounds.json', 'continuous.json', 'render_manifest.json')]
finite, bounds, continuous, visual = map(read, paths)
scripts = ['refine_CAM_root_seating.py', 'audit_CAM_root_seating_math.py',
           'check_CAM_root_seating_continuous.py', 'render_CAM_root_seating.py']
for report, script in zip([finite, bounds, continuous, visual], scripts):
    assert report['status'] == 'PASS' and report['source_main_sha256'] == main_hash
    assert report['script_sha256'] == sha(A8 / script)
    assert not report['main_applied'] and not report['manufacturing_release']
    assert report['whole_harness'] == 'BLOCKED'
assert finite['helper_sha256'] == sha(A8 / 'plan_CAM_root_seating.py')
assert continuous['helper_sha256'] == sha(A8 / 'refine_CAM_root_seating.py')
assert visual['helper_sha256'] == sha(A8 / 'render_CAM_contact_refined_forming.py')
assert finite['source_forming_sha256'] == sha(TC / 'negative_complete/screen.json')
assert finite['source_previous_candidate_sha256'] == sha(RS / 'finite_screen.json')
assert read(RS / 'finite_screen.json')['status'] == 'BLOCKED'
assert bounds['source_finite_sha256'] == continuous['source_finite_sha256'] == sha(paths[0])
assert visual['source_screen_sha256'] == sha(paths[0])
assert continuous['source_math_sha256'] == sha(paths[1])
pool = A8 / 'cam_fan_in/four_bend_transition/pool.json'
assert finite['source_fan_pool_sha256'] == bounds['source_fan_pool_sha256'] == sha(pool)
assert finite['curves_sha256'] == visual['source_curves_sha256'] == sha(OUT / 'curves.npz')
assert continuous['complete_coverage'] and not continuous['unproved_intervals']
intervals = sorted(continuous['passed_intervals'], key=lambda r: r['offset_interval_mm'][0])
assert len(intervals) == 256
assert intervals[0]['offset_interval_mm'][0] == 0. and intervals[-1]['offset_interval_mm'][1] == 1.5
assert all(a['offset_interval_mm'][1] == b['offset_interval_mm'][0] for a, b in zip(intervals, intervals[1:]))
for row in intervals:
    a, b = row['offset_interval_mm']
    assert row['status'] == 'PASS' and 0. < b - a < .00934
    assert abs(row['displacement_bound_mm'] - 3. * (b - a) / 2.) < 1e-12
assert continuous['global_displacement_lipschitz'] == bounds['chosen_global_displacement_lipschitz'] == 3.
assert continuous['own_crimp_exclusion_mm'] == 2. and continuous['own_crimp_boundary_inserted']
assert continuous['wire_OD_mm'] == finite['wire_OD_mm'] == .6604
assert continuous['ordinary_wire_margin_mm'] == finite['ordinary_wire_margin_mm'] == .3
assert continuous['functional_root_bed_margin_mm'] == finite['functional_root_bed_margin_mm'] == 0.
assert continuous['bare_contact_margin_mm'] == 0.
assert continuous['bed_split_difference_mm3'] == finite['bed_split_difference_mm3'] == 0.
fixture = {r['object'] for r in read(TC / 'housing_approach/screen.json')['rigid_checks']}
assert set(finite['source_fixture_ids']) == set(continuous['source_fixture_ids']) == fixture
assert len(fixture) == 219
assert finite['uninstalled_root_tie_parts'] == continuous['uninstalled_root_tie_parts'] == ['CAM_Tie_Band', 'CAM_Tie_Head']
for key in ['initial_terminal_bypass', 'tie_threading_and_tightening', 'physical_handling']:
    assert continuous[key] == 'NOT_TESTED'
assert len(finite['rows']) == 21
for row in finite['rows']:
    assert row['result']['status'] == row['exact_crimp_check']['status'] == 'PASS'
    assert len(row['curves']) == 4
    for curve in row['curves']:
        assert curve['radius_status'] == 'PASS' and curve['minimum_radius_lower_mm'] >= 7.
        assert curve['unresolved_radius_or_length_intervals'] == 0
        assert abs(curve['whole_length_change_mm']) < 1e-10
        assert curve['length_compensation_bound_mm'] < 4.3e-5
        assert curve['terminal_straight_remaining_mm'] > 5.2
assert len(bounds['bezier_spans']) == 5
for span in bounds['bezier_spans']:
    assert span['status'] == 'PASS' and span['coverage'] and not span['unresolved']
    rows = sorted(span['accepted'], key=lambda r: r['offset_interval_mm'][0])
    assert rows[0]['offset_interval_mm'][0] == 0. and rows[-1]['offset_interval_mm'][1] == 1.5
    assert all(a['offset_interval_mm'][1] == b['offset_interval_mm'][0] for a, b in zip(rows, rows[1:]))
    assert all(r['minimum_radius_lower_mm'] >= 7. for r in rows)
# Upper X(Z) quintic retains its entire 16-mm span; only its final straight changes.
upper_radius = 1. / (1.8875 * (10. * math.sqrt(3.) / 3.) / 16. ** 2)
remaining_straight = 7. - 1.5 * bounds['fan_length_derivative_abs_bound'] - 4.3e-5
assert upper_radius > 7. and remaining_straight > 5.2
assert bounds['circular_radius_mm'] == 7.2
assert bounds['free_free_gap_lower_bound_mm'] == continuous['free_free_gap_lower_bound_mm'] > .3
layout = read(RS / 'layout.json')
assert layout['curves_sha256'] == sha(RS / 'initial_curves.npz')
assert layout['source_main_sha256'] == main_hash
saved = np.load(OUT / 'curves.npz')
endpoints = []
for slot in range(4):
    q = saved[f'offset0_slot{slot}']
    old = layout['rows'][slot]
    errors = [float(np.linalg.norm(q[0] - old['fan_start_mm'])),
              float(np.linalg.norm(q[-1] - old['free_end_mm']))]
    assert max(errors) < 1e-7
    endpoints.append(dict(slot=slot, endpoint_error_mm=errors, status='PASS'))
assert visual['physical_source_objects_preserved'] == 214
assert visual['review_sha256'] == sha(OUT / 'review.blend')
for row in visual['images']:
    assert row['sha256'] == sha(OUT / row['file'])
    assert row['all_four_upper_leads_and_contacts_present'] and row['wire_diameter_mm'] == .6604
    assert row['uninstalled_root_tie_parts'] == finite['uninstalled_root_tie_parts']
inputs = paths + [RS / 'layout.json', RS / 'initial_curves.npz', RS / 'finite_screen.json',
                 OUT / 'curves.npz', pool, TC / 'negative_complete/screen.json']
inputs += [A8 / n for n in scripts + ['plan_CAM_root_seating.py', 'inspect_CAM_root_seating.py',
                                    'check_CAM_sequential_continuous.py', 'render_CAM_contact_refined_forming.py']]
result = dict(status='PASS', scope='Receipt consistency, continuous interval coverage, endpoint agreement and analytic supplemental bounds; no physical certification',
    script_sha256=sha(SCRIPT), source_main_sha256=main_hash,
    source_files={str(p.relative_to(ROOT)): sha(p) for p in inputs},
    finite_positions=21, continuous_intervals=256, complete_offset_coverage=[0., 1.5],
    minimum_upper_quintic_radius_lower_mm=upper_radius,
    minimum_terminal_straight_whole_family_lower_mm=remaining_straight,
    four_endpoint_checks=endpoints, full_feed_or_assembly_identity='NOT_TESTED',
    physical_source_objects_preserved=214, main_applied=False, whole_harness='BLOCKED', manufacturing_release=False)
(OUT / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ['status', 'finite_positions', 'continuous_intervals', 'minimum_terminal_straight_whole_family_lower_mm']}))
