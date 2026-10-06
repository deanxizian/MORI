"""Check complete nominal CAM wire stock on the stepped PH entry route.

The bridge is already seated. The head-side terminals are free, with their
temporary upright tails allowed to rise while the body-side PH housing moves.
No source hardware or print geometry is edited. This finite family screen is
not a continuous-motion certificate or a supplier cut-length drawing.
"""
from pathlib import Path
import ast

ATTACHED_SCRIPT = Path(__file__).resolve()
ATTACHED_HELPER = ATTACHED_SCRIPT.parent / 'screen_CAM_PH_shell16_stepped_entry.py'
__file__ = str(ATTACHED_HELPER)
exec(compile(ATTACHED_HELPER.read_text().split('\ntrials=[];', 1)[0],
             str(ATTACHED_HELPER), 'exec'), globals())
__file__ = str(ATTACHED_SCRIPT)
from mathutils.kdtree import KDTree
sys.path.insert(0, str(ATTACHED_SCRIPT.parent / 'body_prefix_v2'))
from curvature_paths import paths

OUT = STOCK_OUT / 'PH_attached_wire_entry'
OUT.mkdir(exist_ok=True)
curve_helper = ATTACHED_SCRIPT.parent / 'screen_CAM_segmented_bridge_feed.py'
self_helper = ATTACHED_SCRIPT.parent / 'screen_CAM_feed_lift_transition.py'
terminal_helper = ATTACHED_SCRIPT.parent / 'screen_CAM_H02_shell_first.py'


def load_functions(path, names):
    source = path.read_text()
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            function_source = ast.get_source_segment(source, node)
            if node.name == 'make_curve':
                function_source = function_source.replace(
                    "planar_first_angle_rad=plane['arc_angles_rad'][0],",
                    "planar_first_angle_rad=plane['arc_angles_rad'][0], "
                    "planar_angles_rad=list(plane['arc_angles_rad']),")
            exec(compile(function_source, str(path), 'exec'), globals())
    assert all(callable(globals()[n]) for n in names)


load_functions(curve_helper, ['line', 'vertical_offset', 'make_curve', 'mutual_check'])
load_functions(self_helper, ['self_check', 'make_terminal', 'material_samples'])
load_functions(terminal_helper, ['terminal_checks'])
pack_path = ATTACHED_SCRIPT.parent / 'body_prefix_v2/packing.json'
pack = json.loads(pack_path.read_text())
joined_path = ATTACHED_SCRIPT.parent / 'joined_entry_screen.json'
joined = json.loads(joined_path.read_text())
assert pack['status'] == body_math['status'] == 'PASS'
assert body_math['source_yaw_route_sha256'] == sha(joined_path)
assert body_math['source_packing_sha256'] == sha(pack_path)
original_errors = [r['curve_chord_error_mm'] for r in lengths]
specifications = {}
for selected in pack['selected']:
    pin = selected['pin']
    first = np.asarray(selected['curve_mm'])
    existing = partial[f'pin{pin}_yaw0']
    assert np.allclose(first, existing[:len(first)], rtol=0, atol=1e-8)
    tail_length = datums['rows'][pin-1]['body_prefix_model_mm'] - selected['analytic_prefix_length_mm']
    assert abs(tail_length - (joined['analytic_staging_length_mm']-17.2-13.)) < 1e-8
    specifications[pin] = dict(selected=selected, exit=existing[0].copy(),
        tail=existing[len(first)-1:].copy(), tail_analytic_length_mm=tail_length)
native_exits = {p: s['exit'].copy() for p, s in specifications.items()}
ph_path = STOCK_OUT / 'PH_shell16_stepped_entry/verification.json'
ph_report = json.loads(ph_path.read_text())
assert ph_report['status'] == 'PASS'
keypoints = [np.zeros(3)] + [np.asarray(r['end_translation_mm']) for r in ph_report['rows']]
identity_matrices = dict(core=I, upper=I, bridge=I)


def own_housing_check(curve, delta):
    """All four own lead roots are allowed to emerge from the common housing."""
    points = curve['points']
    s = np.r_[0., np.linalg.norm(np.diff(points, axis=0), axis=1).cumsum()]
    points = points[s >= 5. - 1e-8]
    moved = housing.translate(delta.tolist())
    mesh = moved.to_mesh64()
    v = np.asarray(mesh.vert_properties[:, :3])
    f = np.asarray(mesh.tri_verts)
    tree = BVHTree.FromPolygons(v, f.tolist(), all_triangles=True)
    bound = OD/2 + MARGIN + curve['curve_chord_error_mm'] + .061
    lo, hi = v.min(0), v.max(0)
    near_points = points[np.all(points >= lo-bound, axis=1) & np.all(points <= hi+bound, axis=1)]
    for q in near_points:
        distance = float(tree.find_nearest(Vector(q))[3])
        if distance < bound:
            return dict(kind='nonlocal_wire_vs_own_PH', pin=curve['pin'], point_mm=q.tolist(),
                        distance_mm=distance, required_bound_mm=bound)
        if np.all(q >= lo) and np.all(q <= hi):
            probe = manifold.Manifold.sphere(.005, 12).translate(q.tolist())
            if (probe ^ moved).volume() > probe.volume()/2:
                return dict(kind='nonlocal_wire_inside_own_PH', pin=curve['pin'], point_mm=q.tolist())
    return None


def check_state(delta, lift_fraction):
    # Only the unattached wire tail moves; the actual bridge remains seated.
    tail_transform = trans(z=float(delta[2] * lift_fraction))
    curves = {}
    for pin in range(1, 5):
        specifications[pin]['exit'] = native_exits[pin] + delta
        curve, failure = make_curve(pin, tail_transform)
        if failure:
            return curves, [], failure
        curves[pin] = curve
        lengths[pin-1]['curve_chord_error_mm'] = curve['curve_chord_error_mm']
        assert abs(curve['analytic_total_mm'] - lengths[pin-1]['full_nominal_allocation_mm']) < 1e-8
        failure = wire_check(pin, curve['points'], identity_matrices) or self_check(curve)
        if not failure:
            failure = own_housing_check(curve, delta)
        if not failure:
            failure = rigid_check(make_terminal(curve, tail_transform), identity_matrices)
        if failure:
            return curves, [], failure
    pairs, failure = mutual_check(curves)
    if not failure:
        failure = terminal_checks(curves, tail_transform)
    return curves, pairs, failure


started = time.time()
trials = []
saved = {}
selected_trial = None
for fraction in [1., .75, .5, .25, 0.]:
    rows = []
    for index, delta in enumerate(keypoints):
        curves, pairs, failure = check_state(delta, fraction)
        for pin, curve in curves.items():
            saved[f'lift{fraction:g}_key{index}_pin{pin}'] = curve['points']
        baseline_differences = {}
        if index == 0:
            for pin, curve in curves.items():
                baseline_differences[str(pin)] = float(np.linalg.norm(
                    material_samples(curve)-material_samples(dict(points=wire[pin])), axis=1).max())
        rows.append(dict(index=index, PH_translation_mm=delta.tolist(), free_tail_Z_lift_mm=float(delta[2]*fraction),
            status='BLOCKED' if failure else 'PASS', failure=failure, pairs=pairs,
            source_baseline_material_sample_difference_mm=baseline_differences,
            curves=[{k:v for k,v in c.items() if k != 'points'} for c in curves.values()]))
        print('PH_ATTACHED_KEY', fraction, index, rows[-1]['status'], failure, round(time.time()-started, 2), flush=True)
        if failure:
            break
    row = dict(lift_fraction=fraction, checked_keypoints=len(rows), planned_keypoints=len(keypoints),
               status='PASS' if len(rows)==len(keypoints) and not rows[-1]['failure'] else 'BLOCKED', rows=rows)
    trials.append(row)
    if row['status'] == 'PASS':
        selected_trial = len(trials)-1
        break

np.savez_compressed(OUT/'curves.npz', **saved)
source_paths = [ph_path, pack_path, joined_path, partial_path, datum_path, body_math_path,
    JOINT_DATA, JOINT_REPORT, curve_helper, self_helper, terminal_helper,
    ATTACHED_SCRIPT.parent/'body_prefix_v2/curvature_paths.py']
report = dict(status='PASS' if selected_trial is not None else 'BLOCKED',
    scope='Finite keypoint family screen of complete nominal CAM wires with a moving PH housing; not continuous assembly',
    script_sha256=sha(ATTACHED_SCRIPT), helper_sha256=sha(ATTACHED_HELPER),
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in source_paths},
    protected_sources=protected, source_main_sha256=source_hash,
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_target_members=sorted(targets), source_target_groups={n:target_group[n] for n in targets},
    shell_transform=shell_t.tolist(), bridge_pose='native/seated',
    present_fixed_wires=4, deferred_wire_ids=deferred_wires, deferred_plugs=deferred_plugs,
    wire_OD_mm=OD, study_clearance_mm=MARGIN, reference_minimum_bend_radius_mm=7.,
    full_nominal_allocations_mm=[r['full_nominal_allocation_mm'] for r in lengths],
    free_head_ends='Unconnected and untied; modeled terminal space remains ASSUMED',
    own_PH_wire_root_exception_mm=5., source_PH_mating_fit='NOT_TESTED',
    trials=trials, selected_trial=selected_trial, curves_sha256=sha(OUT/'curves.npz'),
    continuous_motion='NOT_TESTED', later_H01_H04_installation='NOT_TESTED',
    following_head_assembly='NOT_TESTED', hands_and_tools='NOT_TESTED',
    complete_attached_assembly='BLOCKED', main_applied=False, supplier_cut_lengths=False,
    manufacturing_release=False, elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PH_ATTACHED_DONE', report['status'], round(time.time()-started, 2), flush=True)
