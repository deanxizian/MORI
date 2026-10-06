"""Retain each source bend family during a finite bridge-lift candidate.

This links the settled source geometry to a searched raised configuration.
It checks explicit material-coordinate samples and rejects arc branch jumps;
it does not certify unsampled motion, hands, actual crimp profiles or buildability.
"""
from pathlib import Path

LIFT_SCRIPT = Path(__file__).resolve()
LIFT_HELPER = LIFT_SCRIPT.parent / 'screen_CAM_feed_pose_packing.py'
__file__ = str(LIFT_HELPER)
exec(compile(LIFT_HELPER.read_text().split('\npools = {}', 1)[0],
             str(LIFT_HELPER), 'exec'), globals())
__file__ = str(LIFT_SCRIPT)
from mathutils import Vector

POSE_OUT = OUT
screen_path = POSE_OUT/'screen.json'
verification_path = POSE_OUT/'verification.json'
screen = json.loads(screen_path.read_text())
verified = json.loads(verification_path.read_text())
assert screen['status'] == verified['status'] == 'PASS'
assert verified['screen_sha256'] == sha(screen_path)
assert screen['script_sha256'] == sha(LIFT_HELPER)
assert args.y == 0. and args.z == 18. and args.label == 'lift18'
for p, digest in screen['source_files'].items(): assert sha(PROJECT/p) == digest
OUT = ORDER_OUT/'feed_lift_transition'
OUT.mkdir(exist_ok=True)
STEPS = 37
u_values = np.linspace(0., 1., STEPS)
fixed_shell = shellpose(15., 0., 14.)
source_configuration = {}
pools = {}
counts = Counter()
candidate_results = []
curve_cache = {}


def self_check(curve):
    p = curve['points']
    ds = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.r_[0., ds.cumsum()]
    bound = float(OD+MARGIN+max(ds)+2*curve['curve_chord_error_mm']+.0001)
    kd = KDTree(len(p))
    for i, q in enumerate(p): kd.insert(q, i)
    kd.balance()
    for i, q in enumerate(p):
        for _,j,d in kd.find_range(q, bound):
            if abs(s[j]-s[i]) > 2.:
                return dict(kind='self_return_clearance', indices=[i,j],
                            sampled_distance_mm=float(d), required_bound_mm=bound,
                            local_arclength_exclusion_mm=2.)
    return None


def make_terminal(curve, bridge_transform):
    endpoint = curve['points'][-1]
    r = endpoint[:2]-bridge_transform[:2,3]
    radial = np.r_[r/np.linalg.norm(r), 0.]
    ez = np.array([0.,0.,1.])
    T = np.column_stack([radial, np.cross(ez,radial), ez, endpoint+ez*2.05])
    return manifold.Manifold.cube([1.,1.8,4.1], center=True).minkowski_sum(
        manifold.Manifold.sphere(.31, 48)).transform(T)


def material_samples(curve):
    points = curve['points']
    ds = np.linalg.norm(np.diff(points, axis=0), axis=1)
    s = np.r_[0., ds.cumsum()]
    # Uniform material fractions, not point-index interpolation. Polyline
    # arc-length error is retained in the report; this is a diagnostic only.
    keep = np.r_[True, ds > 1e-10]
    f = s[keep]/s[-1]
    p = points[keep]
    return np.column_stack([np.interp(np.linspace(0.,1.,1001), f, p[:,i]) for i in range(3)])


def check_candidate(pin, endpoint):
    global bt, matrices
    source = specifications[pin]['selected']
    p = endpoint['parameters']
    assert p['family'] == source['planar_path']['family']
    poses = []
    previous = None
    maximum_motion = 0.
    maximum_length_error = 0.
    failure = None
    for index,u in enumerate(u_values):
        bt = trans(z=18.*float(u))
        matrices = dict(core=I, upper=np.linalg.inv(fixed_shell), bridge=np.linalg.inv(bt))
        azimuth = (1-u)*source['entry_azimuth_deg']+u*p['entry_azimuth_deg']
        radius = (1-u)*source['planar_path']['radius_mm']+u*p['planar_radius_mm']
        curve, failure = variant_curve(pin, float(azimuth), float(radius), p['family'], p['elevation_fraction'])
        if failure: break
        curve['candidate_id'] = f"{endpoint['candidate_id']}_pose{index}"
        lengths[pin-1]['curve_chord_error_mm'] = curve['curve_chord_error_mm']
        current = material_samples(curve)
        angles = np.asarray(curve['planar_angles_rad'])
        if previous:
            jump = float(np.max(np.abs(angles-previous['angles'])))
            motion = float(np.linalg.norm(current-previous['samples'],axis=1).max())
            maximum_motion = max(maximum_motion,motion)
            if jump > math.pi:
                failure = dict(kind='arc_branch_jump', maximum_angle_change_rad=jump,
                               material_sample_displacement_mm=motion)
                break
        previous = dict(angles=angles,samples=current)
        maximum_length_error = max(maximum_length_error,
                                   abs(curve['sampled_total_mm']-curve['analytic_total_mm']))
        failure = wire_check(pin,curve['points'],matrices) or self_check(curve)
        if failure: break
        terminal = make_terminal(curve,bt)
        failure = rigid_check(terminal,matrices)
        if failure: break
        poses.append(curve)
    record = dict(candidate_id=endpoint['candidate_id'], pin=pin,
                  status='BLOCKED' if failure else 'PASS',
                  endpoint_parameters=p, starting_parameters=dict(
                      entry_azimuth_deg=source['entry_azimuth_deg'],
                      planar_radius_mm=source['planar_path']['radius_mm'],
                      family=source['planar_path']['family']),
                  passing_positions=len(poses), planned_positions=STEPS,
                  first_failure_index=len(poses) if failure else None,
                  failure=failure, maximum_sampled_material_motion_mm=maximum_motion,
                  maximum_polyline_length_error_mm=maximum_length_error)
    if not failure: curve_cache[endpoint['candidate_id']] = poses
    return record


for pin in range(1,5):
    original = specifications[pin]['selected']['planar_path']['family']
    candidates = [c for c in screen['pools'][str(pin)] if c['parameters']['family']==original]
    result = [check_candidate(pin,c) for c in candidates]
    candidate_results.extend(result)
    pools[pin] = [r for r in result if r['status']=='PASS']
    for r in result: counts['PASS' if r['status']=='PASS' else r['failure']['kind']] += 1
    print('CAM_LIFT_FAMILY',pin,original,len(candidates),len(pools[pin]),
          [r['failure'] for r in result[:2] if r['failure']],round(time.time()-started,2),flush=True)

pair_cache = {}
selected_rows = []


def pair_check(a,b):
    key = (a['candidate_id'],b['candidate_id'])
    if key in pair_cache: return pair_cache[key]
    minimum = math.inf
    fail = None
    for index,(ca,cb) in enumerate(zip(curve_cache[key[0]],curve_cache[key[1]])):
        rows,failure = mutual_check({ca['pin']:ca,cb['pin']:cb})
        minimum = min(minimum,float(rows[0]['surface_gap_lower_bound_mm']))
        if failure:
            fail = dict(index=index,**failure)
            break
        bridge_transform = trans(z=18.*float(u_values[index]))
        ta,tb = make_terminal(ca,bridge_transform),make_terminal(cb,bridge_transform)
        if (ta^tb).volume() > 1e-5:
            fail = dict(index=index,kind='terminal_pair_overlap')
            break
        # Check inflated terminal solid against the other wire, including
        # containment. Terminal's own last attached wire segment is excluded.
        for terminal,other in [(ta,cb),(tb,ca)]:
            mesh=terminal.to_mesh64()
            v=np.asarray(mesh.vert_properties[:,:3])
            f=np.asarray(mesh.tri_verts)
            lo,hi=v.min(0),v.max(0)
            bound=OD/2+other['curve_chord_error_mm']+.026
            p=other['points']
            mask=np.all(p>=lo-bound,axis=1)&np.all(p<=hi+bound,axis=1)
            if not np.any(mask): continue
            tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
            for q in p[mask]:
                closest,normal,_,distance=tree.find_nearest(Vector(q))
                if float(distance)<bound or (Vector(q)-closest).dot(normal)<0:
                    fail=dict(index=index,kind='terminal_other_wire_clearance',other_pin=other['pin'])
                    break
            if fail: break
        if fail: break
    result=dict(status='BLOCKED' if fail else 'PASS',failure=fail,
                surface_gap_lower_bound_mm=minimum)
    pair_cache[key]=result
    return result


search_nodes=0
order=sorted(pools,key=lambda pin:len(pools[pin]))


def select(chosen):
    global search_nodes
    search_nodes+=1
    if len(chosen)==4: return chosen
    for c in pools[order[len(chosen)]]:
        if all(pair_check(p,c)['status']=='PASS' for p in chosen):
            result=select(chosen+[c])
            if result: return result
    return None


chosen=select([]) if all(pools.values()) else None
saved={}
if chosen:
    for c in chosen:
        for index,curve in enumerate(curve_cache[c['candidate_id']]):
            saved[f"pin{c['pin']}_pose{index}"]=curve['points']
    for a,b in itertools.combinations(chosen,2):
        selected_rows.append(dict(a=a['candidate_id'],b=b['candidate_id'],**pair_check(a,b)))
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if chosen else 'BLOCKED',
            scope='Finite source-family-preserving bridge lift; other stages and continuous movement unverified',
            script_sha256=sha(LIFT_SCRIPT),helper_sha256=sha(LIFT_HELPER),
            source_files={**screen['source_files'],str(screen_path.relative_to(PROJECT)):sha(screen_path),
                          str(verification_path.relative_to(PROJECT)):sha(verification_path)},
            protected_sources=protected,source_main_sha256=source_hash,
            source_prints=membership['substituted_unadopted_prints'],
            planned_positions=STEPS,sample_spacing_mm=.5,bridge_lift_mm=18.,
            shell_transform=fixed_shell.tolist(),fixed_body_wires=14,CAM_wires=4,
            body_connection_preserved=True,wire_OD_mm=OD,clearance_mm=MARGIN,
            minimum_nominal_radius_mm=7.,minimum_upright_stock_mm=5.,
            analytic_length_conserved=True,terminal_dimensions_ASSUMED_mm=[1.,1.8,4.1],
            results=candidate_results,counts=dict(counts),search_nodes=search_nodes,
            selected=chosen,selected_pairs=selected_rows,
            pair_diagnostics=[dict(a=k[0],b=k[1],**v) for k,v in pair_cache.items()],
            curves_sha256=sha(OUT/'curves.npz'),
            continuous_movement='NOT_TESTED',arc_branch_screen_only=True,
            remaining_bridge_back_and_bench='NOT_TESTED',hands_and_fixture='NOT_TESTED',
            actual_wire_and_terminal='NOT_TESTED',main_applied=False,
            whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_LIFT_TRANSITION_DONE',report['status'],[c['candidate_id'] for c in chosen] if chosen else None,
      round(time.time()-started,2),flush=True)
