"""Rebuild selected saved pose curves; include self-return and loose terminals.

The result proves a configuration at one explicit body/bridge pose only. It
does not prove that the configuration can be reached during installation.
"""
from pathlib import Path

VERIFY_SCRIPT = Path(__file__).resolve()
VERIFY_HELPER = VERIFY_SCRIPT.parent / 'screen_CAM_feed_pose_packing.py'
__file__ = str(VERIFY_HELPER)
exec(compile(VERIFY_HELPER.read_text().split('\npools = {}', 1)[0], str(VERIFY_HELPER), 'exec'), globals())
__file__ = str(VERIFY_SCRIPT)
screen = json.loads((OUT/'screen.json').read_text())
assert screen['script_sha256'] == sha(VERIFY_HELPER)
assert screen['curves_sha256'] == sha(OUT/'curves.npz')
assert np.array_equal(np.asarray(screen['pose']['bridge']), bt)
assert np.array_equal(np.asarray(screen['pose']['shell']), st)
for p, digest in screen['source_files'].items(): assert sha(PROJECT/p) == digest
raw_curves = np.load(OUT/'curves.npz')
pools = {}
for pin, choices in screen['pools'].items():
    pools[int(pin)] = [dict(c, points=raw_curves[c['candidate_id']]) for c in choices]
self_results = {}
terminal_results = {}
terminal_solids = {}
selected_checks = []


def self_ok(curve):
    key = curve['candidate_id']
    if key in self_results: return self_results[key]['status'] == 'PASS'
    points = curve['points']
    lengths_local = np.linalg.norm(np.diff(points, axis=0), axis=1)
    s = np.r_[0., lengths_local.cumsum()]
    bound = OD+MARGIN+max(lengths_local)+2*curve['curve_chord_error_mm']+.0001
    tree = KDTree(len(points))
    for i, p in enumerate(points): tree.insert(p, i)
    tree.balance()
    failure = None
    for i, p in enumerate(points):
        candidates = [(j, float(d)) for _,j,d in tree.find_range(p, bound) if abs(s[j]-s[i]) > 2.]
        if candidates:
            j,d = min(candidates, key=lambda item:item[1])
            failure = dict(indices=[i,j], sampled_centreline_distance_mm=d,
                           required_bound_mm=float(bound), arclength_separation_mm=float(abs(s[j]-s[i])))
            break
    self_results[key] = dict(status='BLOCKED' if failure else 'PASS', failure=failure,
                             local_arclength_exclusion_mm=2., radius_mm=OD/2)
    return failure is None


def terminal_ok(curve):
    key = curve['candidate_id']
    if key in terminal_results: return terminal_results[key]['status'] == 'PASS'
    endpoint = curve['points'][-1]
    radial = endpoint[:2]-bt[:2,3]
    radial = np.r_[radial/np.linalg.norm(radial), 0.]
    ez = np.array([0.,0.,1.])
    tangent = np.cross(ez, radial)
    T = np.column_stack([radial, tangent, ez, endpoint+ez*4.1/2])
    shape = manifold.Manifold.cube([1.,1.8,4.1], center=True).minkowski_sum(
        manifold.Manifold.sphere(.31, 48)).transform(T)
    terminal_solids[key] = shape
    failure = rigid_check(shape, matrices)
    terminal_results[key] = dict(status='BLOCKED' if failure else 'PASS', failure=failure,
                                 dimensions_mm=[1.,1.8,4.1], clearance_inflation_mm=.31,
                                 evidence='ASSUMED allocation; not manufacturer crimp geometry')
    return failure is None


search_code = VERIFY_HELPER.read_text().split('\ncache = {}', 1)[1].split('\nselected = search', 1)[0]
search_code = 'cache = {}'+search_code
old_loop = '    for curve in pools[order[len(selected)]]:\n'
assert search_code.count(old_loop) == 1
search_code = search_code.replace(old_loop, old_loop+'        if not self_ok(curve) or not terminal_ok(curve): continue\n')
exec(compile(search_code, str(VERIFY_HELPER), 'exec'), globals())
selected = search([]) if all(pools.values()) else None
pairs = []
terminal_pairs = []
terminal_wire_checks = []
if selected:
    for c in selected:
        p = c['parameters']
        rebuilt, failure = variant_curve(c['pin'], p['entry_azimuth_deg'], p['planar_radius_mm'],
                                         p['family'], p['elevation_fraction'])
        assert failure is None and np.array_equal(rebuilt['points'], c['points'])
        assert abs(rebuilt['analytic_total_mm']-lengths[c['pin']-1]['full_nominal_allocation_mm']) < 1e-8
        lengths[c['pin']-1]['curve_chord_error_mm'] = rebuilt['curve_chord_error_mm']
        failure = wire_check(c['pin'], rebuilt['points'], matrices)
        assert failure is None, failure
        selected_checks.append(dict(candidate_id=c['candidate_id'], self_check=self_results[c['candidate_id']],
                                     terminal_check=terminal_results[c['candidate_id']],
                                     regenerated_geometry='PASS', body_and_other_wires='PASS',
                                     analytic_total_mm=rebuilt['analytic_total_mm'],
                                     stock_mm=rebuilt['stock_mm'], parameters=p))
    for a,b in itertools.combinations(selected, 2):
        check = compatible(a,b)
        assert check['status'] == 'PASS'
        pairs.append(dict(a=a['candidate_id'], b=b['candidate_id'], **check))
        ta,tb=terminal_solids[a['candidate_id']],terminal_solids[b['candidate_id']]
        overlap=max(0.,float((ta^tb).volume()))
        assert overlap < 1e-5
        terminal_pairs.append(dict(a=a['candidate_id'],b=b['candidate_id'],
                                   inflated_overlap_mm3=overlap,status='PASS'))
    for a in selected:
        terminal=terminal_solids[a['candidate_id']]
        mesh=terminal.to_mesh64()
        vertices=np.asarray(mesh.vert_properties[:,:3]);faces=np.asarray(mesh.tri_verts)
        lo,hi=vertices.min(0),vertices.max(0)
        tree=BVHTree.FromPolygons(vertices,faces.tolist(),all_triangles=True)
        for b in selected:
            if a['candidate_id']==b['candidate_id']:continue
            points=b['points']
            bound=float(OD/2+b['curve_chord_error_mm']+
                        max(np.linalg.norm(np.diff(points,axis=0),axis=1))/2+.0001)
            mask=np.all(points>=lo-bound,axis=1)&np.all(points<=hi+bound,axis=1)
            for p in points[mask]:
                distance=float(tree.find_nearest(Vector(p))[3])
                assert distance>=bound,(a['candidate_id'],b['candidate_id'],distance,bound)
                probe=manifold.Manifold.sphere(.005,12).translate(p.tolist())
                assert (probe^terminal).volume()<=probe.volume()/2
            terminal_wire_checks.append(dict(terminal=a['candidate_id'],other_wire=b['candidate_id'],
                                             sampled_near_points=int(mask.sum()),
                                             distance_bound_mm=bound,status='PASS'))

record = dict(status='PASS' if selected else 'BLOCKED',
              scope='Single-pose regenerated four-wire geometry, self-return and terminal-allocation checks only',
              script_sha256=sha(VERIFY_SCRIPT), helper_sha256=sha(VERIFY_HELPER),
              screen_sha256=sha(OUT/'screen.json'), curves_sha256=sha(OUT/'curves.npz'),
              source_main_sha256=source_hash, protected_sources=protected,
              selected=[c['candidate_id'] for c in selected] if selected else None,
              selected_checks=selected_checks, selected_pairs=pairs,
              self_checks=self_results, terminal_checks=terminal_results,
              search_nodes=search_nodes, node_limit=NODE_LIMIT, pair_calls=pair_calls,
              pose=screen['pose'], source_objects_present=screen.get('present_source_objects', len(core|upper|bridge)),
              fixed_body_wires=14, CAM_wires=4, mating_allocations=29,
              source_prints=membership['substituted_unadopted_prints'],
              terminal_pairs=terminal_pairs,terminal_other_wire_checks=terminal_wire_checks,
              terminal_check_scope='Inflated assumed envelopes only; not actual crimp geometry or handling proof',
              hands_and_fixture='NOT_TESTED', actual_wire_and_terminal='NOT_TESTED',
              transition_from_settled='NOT_TESTED', continuous_assembly='NOT_TESTED',
              main_applied=False, manufacturing_release=False, whole_harness='BLOCKED',
              elapsed_s=time.time()-started)
(OUT/'verification.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_FEED_POSE_VERIFIED', args.label, record['status'], record['selected'],
      round(time.time()-started, 2), flush=True)
