"""Test a distinct assembly order: CAM leads stay with the body, not the bridge.

This is a finite diagnostic on existing candidate solids. Both complete CAM
wire lengths and the common PH housing remain fixed in body coordinates while
the shell/bridge follows its documented rigid path. All fourteen body wires
are present, using the saved lower H02 candidate. No main geometry is edited.
"""
from pathlib import Path

FIXED_SCRIPT = Path(__file__).resolve()
FIXED_HELPER = FIXED_SCRIPT.parent / 'screen_CAM_body_install_order.py'
__file__ = str(FIXED_HELPER)
exec(compile(FIXED_HELPER.read_text().split('\nstarted=time.time();trials=', 1)[0],
             str(FIXED_HELPER), 'exec'), globals())
__file__ = str(FIXED_SCRIPT)
FIXED_OUT = ORDER_OUT / 'body_fixed_CAM'
FIXED_OUT.mkdir(exist_ok=True)

assert all(sha(PROJECT / p) == h for p, h in protected.items())
h02_path = ORDER_OUT / 'H02_preinstalled/wire_solids.json'
h02_check_path = ORDER_OUT / 'H02_preinstalled/verification.json'
h02_check = json.loads(h02_check_path.read_text())
assert h02_check['status'] == 'PASS'
assert h02_check['wire_solids_sha256'] == sha(h02_path)
for name, row in json.loads(h02_path.read_text()).items():
    assert name in {'H02_1', 'H02_2'}
    m = manifold.Manifold(manifold.Mesh64(np.array(row['vertices_mm']),
                         np.array(row['triangles'], dtype=np.uint64)))
    mesh = m.to_mesh64()
    vertices = np.asarray(mesh.vert_properties[:, :3])
    faces = np.asarray(mesh.tri_verts)
    target_data['fixed_wire_' + name] = (
        m, vertices.min(0), vertices.max(0),
        BVHTree.FromPolygons(vertices, faces.tolist(), all_triangles=True))

assert len([name for name in target_data if name.startswith('fixed_wire_')]) == 14
saved_wires = np.load(STOCK_OUT / 'full_wires.npz')
assert all(np.array_equal(saved_wires['pin' + str(pin)], points)
           for pin, points in wire.items())

# A settled baseline is kept separate from the existing coarse movement samples.
cases = [('settled_baseline', [(I, I)])] + stages
started = time.time()
results = []


def refine_wire_witness(failure, matrices):
    """Do not present a conservative first-hit bound as an actual collision."""
    if failure.get('kind') != 'wire_clearance':
        return
    pin = failure['pin']
    name = failure['obstacle']
    _, lo, hi, tree = target_data[name]
    points = transform_points(wire[pin], matrices[target_group[name]])
    allowance = failure['required_bound_mm']
    mask = np.all(points >= lo - allowance, axis=1) & np.all(points <= hi + allowance, axis=1)
    minimum = min((float(tree.find_nearest(Vector(point))[3]), point.tolist())
                  for point in points[mask])
    distance, point = minimum
    chord = lengths[pin - 1]['curve_chord_error_mm']
    failure['minimum_sample_witness'] = dict(
        point_in_obstacle_frame_mm=point, centreline_to_surface_mm=distance,
        nominal_wire_radius_mm=OD / 2, curve_chord_error_mm=chord,
        sampled_surface_gap_mm=distance - OD / 2,
        intersection_witness=distance + chord + 1e-4 < OD / 2,
        scope='Surface proximity witness at a saved curve sample; not a continuous-path minimum')


for stage, poses in cases:
    failure = None
    checked = 0
    for index, (shell_transform, bridge_transform) in enumerate(poses):
        # Check body-fixed shapes in each obstacle's own reference frame.
        matrices = {'core': I, 'upper': np.linalg.inv(shell_transform),
                    'bridge': np.linalg.inv(bridge_transform)}
        failure = rigid_check(housing, matrices, True)
        if failure is None:
            for pin, points in wire.items():
                failure = (wire_check(pin, points, matrices)
                           or rigid_check(terminals[pin], matrices))
                if failure:
                    break
        checked += 1
        if failure:
            refine_wire_witness(failure, matrices)
            failure.update(index=index, shell_transform=shell_transform.tolist(),
                           bridge_transform=bridge_transform.tolist())
            break
    result = dict(stage=stage, status='BLOCKED' if failure else 'PASS',
                  checked_positions=checked, planned_positions=len(poses), failure=failure)
    results.append(result)
    print('BODY_FIXED_CAM', stage, result['status'], failure, flush=True)

report = dict(
    status='PASS' if all(row['status'] == 'PASS' for row in results) else 'BLOCKED',
    scope='Coarse body-fixed CAM order diagnostic, not a full installation proof',
    source_main_sha256=source_hash, protected_sources=protected,
    script_sha256=sha(FIXED_SCRIPT), helper_sha256=sha(FIXED_HELPER),
    source_files={str(path.relative_to(PROJECT)): sha(path) for path in
                  [h02_path, h02_check_path, STOCK_OUT / 'full_wires.npz', membership_path]},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_objects=209, present_source_objects=len(core | upper | bridge),
    fixed_body_wires=14, CAM_wires=4, mating_allocations=29,
    nominal_CAM_lengths_mm=[row['full_nominal_allocation_mm'] for row in lengths],
    rows=results, housing_motion='Fixed to body/native Motion J5 reference',
    full_wire_shape='Unchanged saved upright stock and body prefix; no hidden shortening',
    source_curve_radius_check='Reused unchanged source geometry; no curve deformation',
    continuous_motion='NOT_TESTED', hands_and_shape_support='NOT_TESTED',
    threading_and_real_contacts='NOT_TESTED', main_applied=False,
    whole_harness='BLOCKED', manufacturing_release=False,
    no_universal_impossibility_claim=True, elapsed_s=time.time() - started)
(FIXED_OUT / 'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
assert all(sha(PROJECT / p) == h for p, h in protected.items())
print('BODY_FIXED_CAM_DONE', report['status'], round(report['elapsed_s'], 2), flush=True)
