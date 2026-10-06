"""Separate shell withdrawal from bridge/CAM lift without changing parts.

The two stages retain the verified six-wire lift boundary exactly. Installed
body mating allocations are included in rigid checks as well as wire checks;
later head plugs are reported separately, not silently discarded.
"""
from pathlib import Path
SHELL_SCRIPT = Path(__file__).resolve()
SHELL_HELPER = SHELL_SCRIPT.parent/'screen_CAM_H02_vertical_withdrawal.py'
__file__ = str(SHELL_HELPER)
exec(compile(SHELL_HELPER.read_text().split('\nrows=[];saved_curves=', 1)[0],
             str(SHELL_HELPER), 'exec'), globals())
__file__ = str(SHELL_SCRIPT)
OUT = ORDER_OUT/'CAM_H02_shell_first'
OUT.mkdir(exist_ok=True)
body_plugs = {n: s.m for n, s in plug.items()
              if n.startswith(('motion_', 'power_', 'imu_'))}
upper_plugs = {n: s.m for n, s in plug.items() if n.startswith('rear_')}
deferred_plugs = sorted(set(plug)-set(body_plugs)-set(upper_plugs))
fixed_rigid.update({'Plug_'+n: m for n, m in body_plugs.items()})
upper_rigid = {n: phys[n] for n in upper}
upper_rigid.update({'Plug_'+n: m for n, m in upper_plugs.items()})
bridge_rigid = {n: phys[n] for n in bridge}
# Actual stage allocations, including plug envelopes, determine separation.
body_max_z = max(m.bounding_box()[5] for m in fixed_rigid.values())
upper_min_z = min(m.transform(shellpose(15., -14., 0.)[:3, :4]).bounding_box()[2]
                  for m in upper_rigid.values())
needed = max(18., body_max_z+1.-upper_min_z+4., body_max_z+1.-bridge_min_z)
endpoint_z = math.ceil(needed*2)/2
assert endpoint_z <= 144.


def placed(items, transform):
    out = {}
    for name, m in items.items():
        q = m.transform(transform[:3, :4])
        out[name] = (q, np.asarray(q.bounding_box()))
    return out


def collisions(a, b):
    for na, (ma, ba) in a.items():
        for nb, (mb, bb) in b.items():
            if np.any(ba[:3] >= bb[3:]) or np.any(bb[:3] >= ba[3:]):
                continue
            v = max(0., float((ma ^ mb).volume()))
            if v > 1e-5:
                return dict(kind='rigid_overlap', a=na, b=nb, intersection_mm3=v)
    return None


def terminal_checks(curves, bt):
    ts = {pin: make_terminal(c, bt) for pin, c in curves.items()}
    for pa, pb in itertools.combinations(sorted(ts), 2):
        v = max(0., float((ts[pa] ^ ts[pb]).volume()))
        if v > 1e-5:
            return dict(kind='terminal_pair_overlap', pins=[pa, pb], intersection_mm3=v)
    for pin, terminal in ts.items():
        mesh = terminal.to_mesh64()
        v = np.asarray(mesh.vert_properties[:, :3]); f = np.asarray(mesh.tri_verts)
        lo, hi = v.min(0), v.max(0)
        tree = BVHTree.FromPolygons(v, f.tolist(), all_triangles=True)
        for other, c in curves.items():
            if pin == other:
                continue
            points = c['points']
            ds = np.linalg.norm(np.diff(points, axis=0), axis=1)
            bound = OD/2+c['curve_chord_error_mm']+float(ds.max())/2+1e-4
            near = points[np.all(points >= lo-bound, axis=1)
                          & np.all(points <= hi+bound, axis=1)]
            for q in near:
                dist = float(tree.find_nearest(Vector(q))[3])
                if dist < bound:
                    return dict(kind='terminal_other_wire_clearance', terminal=pin,
                                wire=other, distance_mm=dist, required_bound_mm=bound)
                if np.all(q >= lo) and np.all(q <= hi):
                    probe = manifold.Manifold.sphere(.005, 12).translate(q.tolist())
                    if (probe ^ terminal).volume() > probe.volume()/2:
                        return dict(kind='wire_inside_terminal', terminal=pin, wire=other)
    return None


fixed_placed = placed(fixed_rigid, I)
phases = [
    ('shell_back_bridge_held', [dict(y=float(y), bz=18., sz=14.)
                                for y in np.linspace(0., -14., 57)]),
    ('vertical_separated_shell', [dict(y=-14., bz=float(z), sz=float(z-4.))
                                  for z in np.arange(18., endpoint_z+.01, .5)]),
]
rows = []; stage_rows = []; saved = {}; previous = {}; failure = None
for label, poses in phases:
    first_row = len(rows)
    for index, pose in enumerate(poses):
        bt = trans(z=pose['bz'])
        st = shellpose(15., pose['y'], pose['sz'])
        matrices = dict(core=I, upper=np.linalg.inv(st), bridge=np.linalg.inv(bt))
        up = placed(upper_rigid, st); bp = placed(bridge_rigid, bt)
        failure = (collisions(up, fixed_placed) or collisions(bp, fixed_placed)
                   or collisions(up, bp) or rigid_check(housing, matrices, True))
        curves = {}; pairs = []
        for pin, params in starts.items():
            if failure:
                break
            c, failure = variant_curve(pin, params['entry_azimuth_deg'],
                                       params['planar_radius_mm'], params['family'],
                                       params['elevation_fraction'])
            if failure:
                break
            if not rows:
                assert np.array_equal(c['points'], source_curves[pin])
            c['candidate_id'] = f'pin{pin}_{label}_{index}'
            angles = np.asarray(c['planar_angles_rad'])
            if pin in previous and np.max(np.abs(angles-previous[pin])) > math.pi:
                failure = dict(kind='arc_branch_jump', pin=pin)
                break
            previous[pin] = angles
            lengths[pin-1]['curve_chord_error_mm'] = c['curve_chord_error_mm']
            failure = (wire_check(pin, c['points'], matrices) or self_check(c)
                       or rigid_check(make_terminal(c, bt), matrices))
            if failure:
                break
            curves[pin] = c
        if failure is None:
            pairs, failure = mutual_check(curves)
        if failure is None:
            failure = terminal_checks(curves, bt)
        for pin, c in curves.items():
            saved[f'{label}_pin{pin}_pose{index}'] = c['points']
        rows.append(dict(stage=label, index=index, pose=pose, shell_tilt_deg=15.,
                         bridge_y_mm=0., status='BLOCKED' if failure else 'PASS',
                         failure=failure, pairs=pairs,
                         curves=[{k:v for k,v in c.items() if k != 'points'}
                                 for c in curves.values()]))
        if failure:
            break
        if index % 30 == 0:
            print('CAM_SHELL_FIRST_PROGRESS', label, index, round(time.time()-started, 2), flush=True)
    stage_rows.append(dict(stage=label, planned_positions=len(poses),
                           checked_positions=len(rows)-first_row,
                           status='BLOCKED' if failure else 'PASS', failure=failure))
    if failure:
        break
np.savez_compressed(OUT/'curves.npz', **saved)
report = dict(
    status='BLOCKED' if failure else 'PASS',
    scope='Two finite stages after six-wire lift; unadopted assembly candidate',
    script_sha256=sha(SHELL_SCRIPT), helper_sha256=sha(SHELL_HELPER),
    source_files={**joint['source_files'], str(joint_path.relative_to(PROJECT)):sha(joint_path),
                  str(joint_check_path.relative_to(PROJECT)):sha(joint_check_path),
                  str((JOINT/'wire_solids.json').relative_to(PROJECT)):sha(JOINT/'wire_solids.json'),
                  str((JOINT/'curves.npz').relative_to(PROJECT)):sha(JOINT/'curves.npz')},
    protected_sources=protected, source_main_sha256=source_hash,
    source_prints=membership['substituted_unadopted_prints'],
    installed_stage=dict(core=sorted(core), upper=sorted(upper), bridge=sorted(bridge),
                         body_plugs=sorted(body_plugs), upper_plugs=sorted(upper_plugs),
                         deferred_head_plugs=deferred_plugs, body_wires=14),
    endpoint_derivation=dict(body_max_z_mm=body_max_z, upper_zero_min_z_mm=upper_min_z,
                             bridge_zero_min_z_mm=bridge_min_z, separation_mm=1.,
                             necessary_bridge_z_mm=needed, rounded_bridge_z_mm=endpoint_z),
    stages=stage_rows, rows=rows, curves_sha256=sha(OUT/'curves.npz'),
    exact_prior_boundary_match=bool(rows and rows[0]['status']=='PASS'),
    full_analytic_wire_length_preserved=True,
    all_mating_allocations_retained_for_wire_checks=True,
    continuous_motion='NOT_TESTED', hands_and_support='NOT_TESTED',
    later_head_assembly='NOT_TESTED', main_applied=False,
    whole_harness='BLOCKED', manufacturing_release=False, elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_SHELL_FIRST_DONE', report['status'], stage_rows, round(time.time()-started,2), flush=True)
