"""Move the bridge-side CAM lead while retaining the native body connection.

The body plug, initial 5 mm exits and quarter bends stay fixed. Planar tangent
paths connect them to variable-height R7 S bends; only the remaining bridge
segment follows the bridge. All original nominal wire material is retained as
explicit upright end stock. This is an independent, bounded assembly study.
"""
from pathlib import Path

SEGMENT_SCRIPT = Path(__file__).resolve()
SEGMENT_HELPER = SEGMENT_SCRIPT.parent / 'screen_CAM_body_fixed_installation.py'
__file__ = str(SEGMENT_HELPER)
exec(compile(SEGMENT_HELPER.read_text().split('\n# A settled baseline', 1)[0],
             str(SEGMENT_HELPER), 'exec'), globals())
__file__ = str(SEGMENT_SCRIPT)
sys.path.insert(0, str(SEGMENT_SCRIPT.parent / 'body_prefix_v2'))
from curvature_paths import paths
from mathutils.kdtree import KDTree

OUT = ORDER_OUT / 'segmented_CAM'
OUT.mkdir(exist_ok=True)
pack_path = SEGMENT_SCRIPT.parent / 'body_prefix_v2/packing.json'
pack = json.loads(pack_path.read_text())
joined_path = SEGMENT_SCRIPT.parent / 'joined_entry_screen.json'
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
    tail = existing[len(first)-1:]
    tail_length = datums['rows'][pin-1]['body_prefix_model_mm']-selected['analytic_prefix_length_mm']
    assert abs(tail_length-(joined['analytic_staging_length_mm']-17.2-13.)) < 1e-8
    specifications[pin] = dict(
        selected=selected, exit=existing[0], tail=tail,
        tail_analytic_length_mm=tail_length)


def line(a, b, step=.05):
    return np.linspace(a, b, max(2, math.ceil(float(np.linalg.norm(b-a)) / step)+1))


def vertical_offset(entry, terminal, radial, radius=7.):
    """Tangent horizontal-to-horizontal offset, with optional vertical span."""
    delta = float(terminal[2] - entry[2])
    sign = 1. if delta >= 0 else -1.
    height = abs(delta)
    theta = math.acos(max(-1., 1-height/(2*radius))) if height <= 2*radius else math.pi/2
    run = 2*radius*math.sin(theta)
    start = terminal + radial*run
    start[2] = entry[2]
    if theta < 1e-9:
        return start, start[None, :], 0., 0.
    t = np.linspace(0., theta, max(2, math.ceil(radius*theta/.05)+1))
    ez = np.array([0., 0., sign])
    first = np.array([start-radial*radius*math.sin(a)+ez*radius*(1-math.cos(a)) for a in t])
    middle = first[-1]
    span = max(0., height-2*radius)
    straight = line(middle, middle+ez*span)
    middle = straight[-1]
    last = np.array([middle-radial*radius*(math.sin(theta)-math.sin(a))
                     +ez*radius*(math.cos(a)-math.cos(theta)) for a in t[::-1]])
    points = np.vstack([first, straight[1:], last[1:]])
    assert np.linalg.norm(points[-1]-terminal) < 1e-7
    return start, points, 2*radius*theta+span, radius*(1-math.cos(theta/(len(t)-1)/2))


def make_curve(pin, bridge_transform):
    spec = specifications[pin]
    selected = spec['selected']
    e = spec['exit']
    a = e + [0., 0., 5.]
    radius = selected['entry_bend_radius_mm']
    azimuth = math.radians(selected['entry_azimuth_deg'])
    heading = np.array([math.cos(azimuth), math.sin(azimuth), 0.])
    theta = np.linspace(0., math.pi/2, 121)
    entry = np.array([a+radius*(1-math.cos(t))*heading+[0., 0., radius*math.sin(t)] for t in theta])
    angle = math.radians(selected['azimuth_deg'])
    radial = np.array([math.cos(angle), math.sin(angle), 0.])
    tail = transform_points(spec['tail'], bridge_transform)
    end, offset, offset_length, offset_error = vertical_offset(entry[-1], tail[0], radial)
    choices = list(paths(entry[-1, :2], heading[:2], end[:2], -radial[:2],
                         selected['planar_path']['radius_mm']))
    chosen = [p for p in choices if p['family'] == selected['planar_path']['family']]
    if len(chosen) != 1:
        return None, dict(pin=pin, kind='tangent_family_unavailable',
                          family=selected['planar_path']['family'], available=[p['family'] for p in choices])
    plane = chosen[0]
    xy = plane['points_xy_mm']
    planar = np.column_stack([xy, np.full(len(xy), entry[-1, 2])])
    assert np.linalg.norm(planar[-1]-offset[0]) < 1e-7
    prefix = np.vstack([line(e, a), entry[1:], planar[1:], offset[1:], tail[1:]])
    analytic_prefix_length = 5. + radius*math.pi/2 + plane['analytic_length_mm'] + offset_length + spec['tail_analytic_length_mm']
    stock = lengths[pin-1]['full_nominal_allocation_mm']-analytic_prefix_length
    if stock < 5.:
        return None, dict(pin=pin, kind='insufficient_upright_end_stock', stock_mm=stock,
                          analytic_prefix_mm=analytic_prefix_length, minimum_stock_mm=5.)
    extra = line(tail[-1], tail[-1]+[0., 0., stock])
    full = np.vstack([prefix, extra[1:]])
    error = max(original_errors[pin-1], plane['chord_error_mm'], offset_error,
                radius*(1-math.cos((theta[1]-theta[0])/2)))
    return dict(points=full, curve_chord_error_mm=error, pin=pin,
                stock_mm=stock, prefix_analytic_mm=analytic_prefix_length,
                analytic_total_mm=analytic_prefix_length+stock,
                sampled_total_mm=float(np.linalg.norm(np.diff(full, axis=0), axis=1).sum()),
                planar_family=plane['family'], planar_length_mm=plane['analytic_length_mm'],
                offset_analytic_mm=offset_length,
                planar_first_angle_rad=plane['arc_angles_rad'][0],
                source_radius_reused=True), None


def mutual_check(curves):
    samples = {}
    for pin, curve in curves.items():
        points = curve['points']
        kd = KDTree(len(points))
        for i, p in enumerate(points): kd.insert(p, i)
        kd.balance()
        samples[pin] = kd
    rows = []
    for a, b in itertools.combinations(curves, 2):
        ca, cb = curves[a], curves[b]
        closest = min(float(samples[b].find(p)[2]) for p in ca['points'])
        uncertainty = (max(np.linalg.norm(np.diff(ca['points'], axis=0), axis=1))
                       +max(np.linalg.norm(np.diff(cb['points'], axis=0), axis=1)))/2
        gap = closest-OD-uncertainty-ca['curve_chord_error_mm']-cb['curve_chord_error_mm']-.0001
        row = dict(a=a, b=b, surface_gap_lower_bound_mm=gap)
        rows.append(row)
        if gap < MARGIN:
            return rows, dict(kind='CAM_mutual_coarse_clearance', **row)
    return rows, None


started = time.time()
rows = []
saved = {}
cases = [('settled_baseline', [(I, I)])] + stages
for stage, poses in cases:
    results = []
    for index, (shell_transform, bridge_transform) in enumerate(poses):
        curves = {}
        failure = None
        for pin in range(1, 5):
            curve, failure = make_curve(pin, bridge_transform)
            if failure: break
            curves[pin] = curve
            lengths[pin-1]['curve_chord_error_mm'] = curve['curve_chord_error_mm']
        matrices = dict(core=I, upper=np.linalg.inv(shell_transform), bridge=np.linalg.inv(bridge_transform))
        if failure is None:
            failure = rigid_check(housing, matrices, True)
        if failure is None:
            for pin, curve in curves.items():
                failure = wire_check(pin, curve['points'], matrices)
                if failure: break
        pairs = []
        if failure is None:
            pairs, failure = mutual_check(curves)
        for pin, curve in curves.items():
            saved[f'{stage}_{index}_pin{pin}'] = curve['points']
        results.append(dict(index=index, status='BLOCKED' if failure else 'PASS', failure=failure,
                            shell_transform=shell_transform.tolist(), bridge_transform=bridge_transform.tolist(),
                            curves=[{k:v for k,v in c.items() if k != 'points'} for c in curves.values()], pairs=pairs))
        if failure: break
    row = dict(stage=stage, status='PASS' if all(r['status']=='PASS' for r in results) else 'BLOCKED',
               planned_positions=len(poses), checked_positions=len(results), rows=results)
    rows.append(row)
    print('SEGMENTED_CAM', stage, row['status'], len(results), results[-1]['failure'], flush=True)

np.savez_compressed(OUT/'curves.npz', **saved)
report = dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
              scope='Finite constant-analytic-material CAM body/bridge feed diagnostic, not full assembly',
              script_sha256=sha(SEGMENT_SCRIPT), helper_sha256=sha(SEGMENT_HELPER),
              protected_sources=protected, source_main_sha256=source_hash,
              source_files={str(p.relative_to(PROJECT)):sha(p) for p in
                            [pack_path, joined_path, body_math_path, partial_path, datum_path, h02_path, h02_check_path,
                             SEGMENT_SCRIPT.parent/'body_prefix_v2/curvature_paths.py', membership_path]},
              substituted_unadopted_prints=membership['substituted_unadopted_prints'],
              wire_OD_mm=OD, reference_radius_mm=7., clearance_mm=MARGIN,
              fixed_body_wires=14, body_connection_preserved=True,
              original_nominal_allocations_mm=[r['full_nominal_allocation_mm'] for r in lengths],
              rows=rows, curves_sha256=sha(OUT/'curves.npz'),
              source_tail_radius_reused=True, wire_self_clearance='NOT_TESTED',
              continuous_movement='NOT_TESTED', terminal_space_and_hands='NOT_TESTED',
              subsequent_head_assembly='NOT_TESTED', main_applied=False,
              manufacturing_release=False, whole_harness='BLOCKED', elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SEGMENTED_CAM_DONE', report['status'], round(time.time()-started, 2), flush=True)
