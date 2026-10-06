"""Assemble independent continuous receipts, without recertifying physical fit."""
from pathlib import Path
import hashlib
import json
import math

SCRIPT = Path(__file__).resolve()
A8 = SCRIPT.parent
ROOT = A8.parents[3]
TC = A8 / 'cam_wire_forming/lifted_end2/contact_refined_forming'
OUT = TC / 'negative_complete'
read = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

files = {
    'first_three': TC / 'first_three_continuous/screen.json',
    'prefix': TC / 'negative_prefix/screen.json',
    'return': TC / 'negative_return_branch/screen.json',
    'tail': TC / 'negative_tail/screen.json',
    'junctions': OUT / 'junctions.json',
}
reports = {name: read(path) for name, path in files.items()}
main = ROOT / 'mechanical/mori_v1_2.blend'
main_hash = sha(main)
helper_hash = sha(A8 / 'check_CAM_sequential_continuous.py')
scripts = dict(first_three='check_CAM_first_three_continuous.py',
               prefix='plan_CAM_negative_prefix.py',
               return_='check_CAM_negative_return_edges.py',
               tail='check_CAM_negative_tail.py',
               junctions='check_CAM_forming_junctions.py')
scripts['return'] = scripts.pop('return_')
for name, report in reports.items():
    assert report['status'] == 'PASS', (name, report['status'])
    assert report['source_main_sha256'] == main_hash
    assert report['helper_sha256'] == helper_hash
    assert report['script_sha256'] == sha(A8 / scripts[name])
    assert not report['main_applied'] and not report['manufacturing_release']
    assert report['whole_harness'] == 'BLOCKED'
    if name != 'junctions':
        assert not report.get('unproved_intervals')
        assert not report.get('nominal_intermediate_failures')
        assert report.get('error') is None
        assert report['ordinary_margin_mm'] == .3
        assert report['bare_contact_margin_mm'] == 0.
    assert report['generic_0_3mm_contact_packing'] == 'BLOCKED'

first, last, junctions = (reports[name] for name in ['first_three', 'tail', 'junctions'])
assert first['complete_first_three_coverage']
assert last['complete_last_wire_coverage'] and last['complete_tail_coverage']
assert last['source_prefix_sha256'] == sha(files['prefix'])
assert last['source_return_sha256'] == sha(files['return'])
assert junctions['source_last_wire_sha256'] == sha(files['tail'])
assert junctions['all_conductors_retained']
assert len(junctions['endpoints']) == 8
assert all(row['status'] == 'PASS' for row in junctions['endpoints'])
original_file = TC / 'screen.json'
original = read(original_file)
assert first['source_path_sha256'] == sha(original_file)
assert junctions['source_original_path_sha256'] == sha(original_file)
assert original['wire_order'] == junctions['wire_order'] == [3, 2, 1, 0]
keys = ['fraction', 'amplitude_mm', 'side_angle_deg']
paths = [[{key: node[key] for key in keys} for node in stage['path']]
         for stage in original['stages'][:3]] + [last['path']]
parameters = junctions['forming_curve_parameters']
# At each fixed material coordinate u, the planar tangent has unit norm.
# Its angle changes with time, but x'(u) does not: |r'(u)|=sqrt(1+x'(u)^2).
# Hence the material length is invariant. The x acceleration is orthogonal
# to the planar acceleration; do not add the two magnitudes unnecessarily.
minimum_planar_radius = min(parameters['upper_radius_mm'], parameters['lower_radius_mm'])
maximum_x_acceleration = (10. * math.sqrt(3.) / 3.) * parameters['lateral_quintic_shift_mm'] / parameters['lateral_quintic_span_mm'] ** 2
curvature_bound = math.hypot(1. / minimum_planar_radius, maximum_x_acceleration)
minimum_radius_bound = 1. / curvature_bound
maximum_amplitude = max(node['amplitude_mm'] for path in paths for node in path)
assert min(node['amplitude_mm'] for path in paths for node in path) >= 0.
remaining_return_straight = parameters['planar_segments_mm'][2] - maximum_amplitude
assert remaining_return_straight > .49
all_intervals = first['passed_intervals'] + last['combined_intervals']
coverage = []
for stage, path in enumerate(paths):
    rows = sorted([row for row in all_intervals if row['stage'] == stage],
                  key=lambda row: row['interval'][0])
    assert rows and path[0]['fraction'] == rows[0]['interval'][0] == 0.
    assert path[-1]['fraction'] == rows[-1]['interval'][1] == 1.
    assert all(a['fraction'] < b['fraction'] for a, b in zip(path, path[1:]))
    assert all(a['interval'][1] == b['interval'][0] for a, b in zip(rows, rows[1:]))
    for row in rows:
        a, b = row['interval']
        assert row['status'] == 'PASS' and a < b
        assert any(n['fraction'] - 1e-12 <= a and b <= m['fraction'] + 1e-12
                   for n, m in zip(path, path[1:])), (stage, a, b)
    coverage.append(dict(stage=stage, geometric_slot=[3, 2, 1, 0][stage],
                         parameter_interval=[0., 1.], continuous_coverage='PASS',
                         interval_count=len(rows), control_node_count=len(path)))

inputs = {str(path.relative_to(ROOT)): sha(path) for path in files.values()}
for filename in [*scripts.values(), 'check_CAM_sequential_continuous.py',
                 'refine_CAM_outer_contact_path.py']:
    path = A8 / filename
    inputs[str(path.relative_to(ROOT))] = sha(path)
inputs[str(original_file.relative_to(ROOT))] = sha(original_file)
report = dict(
    status='PASS',
    scope='Prescribed four-wire nominal forming motion only; closed continuous coverage of four stages',
    script_sha256=sha(SCRIPT), source_main_sha256=main_hash,
    helper_sha256=helper_hash, source_files=inputs,
    wire_order=[3, 2, 1, 0], wire_order_is_electrical_pinmap=False,
    stages=[dict(stage=i, active_slot=[3, 2, 1, 0][i], path=path)
            for i, path in enumerate(paths)],
    coverage=coverage, continuous_interval_count=len(all_intervals),
    complete_four_wire_forming_coverage=True, stage_boundary_identity='PASS',
    retained_static_wire_pairs=len(first['static_wire_pairs']) + len(junctions['last_stage_static_wire_pairs']),
    fixed_upstream_and_body_wires_retained=True,
    nominal_bare_contacts_retained=True, wire_outer_diameter_mm=.6604,
    material_length_invariant='PASS',
    material_length_basis='Fixed x quintic and unit-speed planar tangent give sqrt(1+x_prime(u)^2), independent of forming controls; lateral turn is a rigid rotation',
    nominal_curve_radius_lower_bound_mm=minimum_radius_bound,
    nominal_curve_curvature_upper_bound_per_mm=curvature_bound,
    geometry_formula_parameters=parameters,
    shortest_return_straight_lower_bound_mm=remaining_return_straight,
    bend_bound_is_material_qualification=False,
    ordinary_margin_mm=.3, bare_contact_margin_mm=0.,
    generic_0_3mm_contact_packing='BLOCKED',
    contact_evidence='ASSUMED boxes from JST catalogue spans; not measured post-crimp parts',
    robot_pose='Yaw0 / pitch0; fixture set defined by the continuous helper; display carrier, CAM board and head shells not yet installed',
    final_plug_lift_mm=2., feed_to_start='NOT_TESTED',
    terminal_insertion='NOT_TESTED', ties='NOT_TESTED',
    other_seven_cross_joint_wires='NOT_TESTED',
    complete_connected_installation='BLOCKED',
    real_wire_material_behavior='NOT_TESTED',
    main_applied=False, whole_harness='BLOCKED', manufacturing_release=False)
OUT.mkdir(exist_ok=True)
(OUT / 'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
assert sha(main) == main_hash
print(json.dumps({'status': report['status'], 'coverage': coverage,
                  'continuous_interval_count': len(all_intervals)}, ensure_ascii=False))
