"""Keep the body-side underpass and elevate only the lead after it clears H01.

Two tangent vertical offsets retain R7 bends. The initial body plug and quarter
bend are fixed. Nominal material is conserved by releasing upright end stock.
This is an unadopted finite candidate on the existing provisional print shapes.
"""
from pathlib import Path

ELEVATED_SCRIPT = Path(__file__).resolve()
ELEVATED_HELPER = ELEVATED_SCRIPT.parent / 'screen_CAM_segmented_bridge_feed.py'
__file__ = str(ELEVATED_HELPER)
exec(compile(ELEVATED_HELPER.read_text().split('\nstarted = time.time()', 1)[0],
             str(ELEVATED_HELPER), 'exec'), globals())
__file__ = str(ELEVATED_SCRIPT)
OUT = ORDER_OUT / 'elevated_CAM'
OUT.mkdir(exist_ok=True)


def make_elevated_curve(pin, bridge_transform, elevation_fraction=1.):
    spec = specifications[pin]
    selected = spec['selected']
    e = spec['exit']
    a = e+[0., 0., 5.]
    radius = selected['entry_bend_radius_mm']
    azimuth = math.radians(selected['entry_azimuth_deg'])
    heading = np.array([math.cos(azimuth), math.sin(azimuth), 0.])
    theta = np.linspace(0., math.pi/2, 121)
    entry = np.array([a+radius*(1-math.cos(t))*heading+[0., 0., radius*math.sin(t)] for t in theta])
    lift = float(bridge_transform[2, 3])*elevation_fraction
    turn = math.acos(1-lift/(2*radius)) if lift <= 2*radius else math.pi/2
    run = 2*radius*math.sin(turn)
    lift_end = entry[-1]+heading*run+[0., 0., lift]
    lift_start, elevator, elevator_length, elevator_error = vertical_offset(entry[-1], lift_end, -heading, radius)
    assert np.linalg.norm(lift_start-entry[-1]) < 1e-8
    angle = math.radians(selected['azimuth_deg'])
    radial = np.array([math.cos(angle), math.sin(angle), 0.])
    tail = transform_points(spec['tail'], bridge_transform)
    end, offset, offset_length, offset_error = vertical_offset(lift_end, tail[0], radial)
    choices = list(paths(lift_end[:2], heading[:2], end[:2], -radial[:2],
                         selected['planar_path']['radius_mm']))
    chosen = [p for p in choices if p['family'] == selected['planar_path']['family']]
    if len(chosen) != 1:
        return None, dict(pin=pin, kind='tangent_family_unavailable',
                          family=selected['planar_path']['family'], available=[p['family'] for p in choices])
    plane = chosen[0]
    xy = plane['points_xy_mm']
    planar = np.column_stack([xy, np.full(len(xy), lift_end[2])])
    assert np.linalg.norm(planar[-1]-offset[0]) < 1e-7
    prefix = np.vstack([line(e, a), entry[1:], elevator[1:], planar[1:], offset[1:], tail[1:]])
    analytic_prefix = (5.+radius*math.pi/2+elevator_length+plane['analytic_length_mm']
                       +offset_length+spec['tail_analytic_length_mm'])
    stock = lengths[pin-1]['full_nominal_allocation_mm']-analytic_prefix
    if stock < 5.:
        return None, dict(pin=pin, kind='insufficient_upright_end_stock', stock_mm=stock,
                          analytic_prefix_mm=analytic_prefix, minimum_stock_mm=5.)
    full = np.vstack([prefix, line(tail[-1], tail[-1]+[0., 0., stock])[1:]])
    error = max(original_errors[pin-1], plane['chord_error_mm'], elevator_error, offset_error,
                radius*(1-math.cos((theta[1]-theta[0])/2)))
    return dict(points=full, curve_chord_error_mm=error, pin=pin,
                elevation_fraction=elevation_fraction, lift_mm=lift, stock_mm=stock,
                prefix_analytic_mm=analytic_prefix, analytic_total_mm=analytic_prefix+stock,
                sampled_total_mm=float(np.linalg.norm(np.diff(full, axis=0), axis=1).sum()),
                planar_family=plane['family'], planar_length_mm=plane['analytic_length_mm'],
                elevator_analytic_mm=elevator_length, offset_analytic_mm=offset_length,
                planar_angles_rad=plane['arc_angles_rad'], source_radius_reused=True), None


started = time.time()
rows = []
saved = {}
for stage, poses in [('settled_baseline', [(I, I)])]+stages:
    results = []
    for index, (shell_transform, bridge_transform) in enumerate(poses):
        curves = {}
        failure = None
        for pin in range(1, 5):
            curve, failure = make_elevated_curve(pin, bridge_transform)
            if failure: break
            curves[pin] = curve
            lengths[pin-1]['curve_chord_error_mm'] = curve['curve_chord_error_mm']
        matrices = dict(core=I, upper=np.linalg.inv(shell_transform), bridge=np.linalg.inv(bridge_transform))
        if failure is None: failure = rigid_check(housing, matrices, True)
        if failure is None:
            for pin, curve in curves.items():
                failure = wire_check(pin, curve['points'], matrices)
                if failure: break
        pairs = []
        if failure is None: pairs, failure = mutual_check(curves)
        for pin, curve in curves.items(): saved[f'{stage}_{index}_pin{pin}'] = curve['points']
        results.append(dict(index=index, status='BLOCKED' if failure else 'PASS', failure=failure,
                            shell_transform=shell_transform.tolist(), bridge_transform=bridge_transform.tolist(),
                            curves=[{k:v for k,v in c.items() if k != 'points'} for c in curves.values()], pairs=pairs))
        if failure: break
    row = dict(stage=stage, status='PASS' if all(r['status']=='PASS' for r in results) else 'BLOCKED',
               planned_positions=len(poses), checked_positions=len(results), rows=results)
    rows.append(row)
    print('ELEVATED_CAM', stage, row['status'], len(results), results[-1]['failure'], flush=True)

np.savez_compressed(OUT/'curves.npz', **saved)
report = dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
              scope='Finite two-offset constant-material CAM feed diagnostic, not full assembly',
              script_sha256=sha(ELEVATED_SCRIPT), helper_sha256=sha(ELEVATED_HELPER),
              protected_sources=protected, source_main_sha256=source_hash,
              source_files={str(p.relative_to(PROJECT)):sha(p) for p in
                            [pack_path, joined_path, body_math_path, partial_path, datum_path, h02_path, h02_check_path,
                             ELEVATED_SCRIPT.parent/'body_prefix_v2/curvature_paths.py', membership_path]},
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
print('ELEVATED_CAM_DONE', report['status'], round(time.time()-started, 2), flush=True)
