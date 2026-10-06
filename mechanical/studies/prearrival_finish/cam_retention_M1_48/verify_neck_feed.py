"""Rebuild bounded verification sweeps on M1.48 without legacy initialization.

The earlier replay used the 0.32 mm cutting solids themselves. Here the
verification padding is 0.31 mm, with the polygonal inradius and interpolation
error explicitly deducted. The required physical gap remains 0.3 mm. Neither
the candidate parts nor the main model are changed.
"""
from pathlib import Path
import sys, json, time, math, itertools
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from current_context import RetentionContext, PROJECT, np, manifold, sha, cache, overlap_boxes

ctx = RetentionContext(); started = time.time()
source = HERE.parent / 'harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate'
build = json.loads((source / 'construction.json').read_text())
old = json.loads((source / 'verification.json').read_text())
assert old['source_construction_sha256'] == sha(source / 'construction.json')
assert build['contact_dimensions_mm'] == [1., 1.8, 4.1]
path_file = source / 'lower_bend/selected_path.npz'
curve_file = source / 'wire_relaxation_curves.npz'
assert sha(path_file) == build['temporary_guide_path_sha256']
assert sha(curve_file) == build['wire_curves_sha256']
trajectory = np.load(path_file)['radial_z_axis_angle']
wire_curves = np.load(curve_file)
targets = ctx.targets.copy()
for name in ['Pitch_Yoke', 'Pitch_Cradle']:
    targets[name] = ctx.read(HERE / (name + '.npz'))
pad = .31; dims = np.asarray(build['contact_dimensions_mm'])
sphere = manifold.Manifold.sphere(pad, 48)
mesh = sphere.to_mesh64(); vertices = np.asarray(mesh.vert_properties[:, :3]); faces = np.asarray(mesh.tri_verts)
a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
normals = np.cross(b-a, c-a)
inradius = float(np.min(np.abs(np.einsum('ij,ij->i', a, normals)) / np.linalg.norm(normals, axis=1)))
delta_angle = float(np.max(np.abs(np.diff(trajectory[:, 2]))))
terminal_error = (10. + dims[2] + np.linalg.norm(dims[:2]/2) + pad) * delta_angle**2/8 + 1e-6
wire_error = 10. * delta_angle**2/8 + 1e-6
terminal_gap = inradius - terminal_error
wire_gap = inradius/pad * .64 - wire_error - .3302
assert terminal_gap > .3 and wire_gap > .3
terminal = manifold.Manifold.cube(dims.tolist(), center=True).minkowski_sum(sphere)
wire_sphere = manifold.Manifold.sphere(.64, 48)

def hits(m):
    results = []
    for name, target in targets.items():
        if not overlap_boxes(m, target): continue
        volume = max(0., float((m ^ target).volume()))
        if volume > 1e-7:
            results.append(dict(target=name, padded_overlap_mm3=volume))
    return results

rows = []; sweeps = {}
for phase in [45, 135, 225, 315]:
    angle = math.radians(phase)
    er = np.array([math.cos(angle), math.sin(angle), 0.]); ez = np.array([0., 0., 1.]); et = np.cross(ez, er)
    transforms = []
    for r, z, theta in trajectory:
        axis = er * math.sin(theta) + ez * math.cos(theta)
        x = er * math.cos(theta) - ez * math.sin(theta)
        transforms.append(np.column_stack([x, et, axis, r*er + z*ez + axis*dims[2]/2]))
    instances = [terminal.transform(t) for t in transforms]
    spans = []; i = 0
    while i < len(transforms)-1:
        j = i+1
        while j+1 < len(transforms) and np.max(np.abs(transforms[j+1][:, :3]-transforms[i][:, :3])) < 1e-12:
            if np.linalg.norm(np.cross(transforms[j+1][:, 3]-transforms[i][:, 3], transforms[j][:, 3]-transforms[i][:, 3])) > 1e-9: break
            j += 1
        spans.append((i, j)); i = j
    contact = manifold.Manifold.batch_boolean([
        manifold.Manifold.batch_hull([instances[i], instances[j]]) for i, j in spans], manifold.OpType.Add)
    new = wire_curves[f'phase{phase}_new']; old_points = wire_curves[f'phase{phase}_old']
    wire = manifold.Manifold.batch_boolean([
        manifold.Manifold.batch_hull([wire_sphere.translate(p.tolist())
            for p in [new[i], new[j], old_points[i], old_points[j]]]) for i, j in spans], manifold.OpType.Add)
    for kind, shape in [('contact', contact), ('wire', wire)]:
        assert shape.status() == manifold.Error.NoError and shape.volume() > 0
        cache(HERE / f'feed_{kind}_{phase}.npz', shape)
        conflicts = hits(shape)
        rows.append(dict(phase_deg=phase, kind=kind, spans=len(spans),
                         status='BLOCKED' if conflicts else 'PASS', hits=conflicts))
        sweeps[kind, phase] = shape
        print('CURRENT_BOUNDED_FEED', rows[-1], flush=True)
pairs = []
for a, b in itertools.combinations([45, 135, 225, 315], 2):
    cases = []
    for ka, kb in itertools.product(['contact', 'wire'], repeat=2):
        left, right = sweeps[ka, a], sweeps[kb, b]
        volume = max(0., float((left ^ right).volume())) if overlap_boxes(left, right) else 0.
        cases.append(dict(a=ka, b=kb, padded_overlap_mm3=volume))
    pairs.append(dict(phases=[a, b], status='PASS' if all(r['padded_overlap_mm3'] <= 1e-7 for r in cases) else 'BLOCKED', cases=cases))
ctx.assert_unchanged()
report = dict(status='PASS' if all(r['status']=='PASS' for r in rows+pairs) else 'BLOCKED',
    scope='Bounded continuous local terminal passage and affine neck-wire relaxation; no full-length feed proof',
    **ctx.evidence(), script_sha256=sha(__file__), context_sha256=sha(HERE/'current_context.py'),
    source_files={str(p.relative_to(PROJECT)): sha(p) for p in [path_file, curve_file, source/'construction.json', source/'verification.json']},
    contact_dimensions_mm=dims.tolist(), contact_evidence=build['contact_evidence'],
    clearance_requirement_mm=.3, terminal_padding_mm=pad, padding_inradius_mm=inradius,
    terminal_interpolation_error_mm=float(terminal_error), wire_interpolation_error_mm=wire_error,
    terminal_gap_lower_bound_mm=float(terminal_gap), wire_gap_lower_bound_mm=wire_gap,
    boolean_overlap_tolerance_mm3=1e-7, rows=rows, pairs=pairs,
    diagnostic_replay='neck_feed.json used the construction cutting solids at 0.32 mm; small boundary overlaps were not waived. Verification sweeps rebuilt independently at 0.31 mm, still above the original 0.3 mm clearance after errors.',
    closed_ties='Not installed yet', all_robot_solids_included=209, mating_allocations=29, fixed_candidate_wires=14,
    actual_terminal_shape='BLOCKED', complete_wire_material='NOT_TESTED', full_sequence='NOT_TESTED',
    elapsed_s=time.time()-started)
(HERE/'neck_feed_verified.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
print('CURRENT_BOUNDED_FEED_DONE', report['status'], flush=True)
