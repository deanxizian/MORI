"""Recheck the selected J5-to-neck candidates against explicit native inputs.

This verifies installed fixed curves only. It is not an assembly simulation,
a complete CAM harness, or evidence for physical cable bend life.
"""
from pathlib import Path
import sys, json, math, itertools, time
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from native_context import *
from validate import rigidtr

ctx = Context()
started = time.time()
selection_path = HERE / 'packing.json'
d = json.loads(selection_path.read_text())
assert d['status'] == 'PASS' and d['source_main_sha256'] == ctx.source_hash
curve_path = HERE / 'packed_curves.npz'
curves = np.load(curve_path)
source_curves = np.load(HERE / 'body_prefix_curves.npz')
radius = d['wire_OD_mm'] / 2
gap = d['surface_gap_requirement_mm']
checks = []
paths = {}
bounds = {}

for row in d['selected']:
    pin = row['pin']
    p = curves[f'pin{pin}']
    assert np.array_equal(p, source_curves[row['candidate_id']])
    error = row['error_bound_mm']
    paths[pin] = p
    steps = np.linalg.norm(np.diff(p, axis=0), axis=1)
    assert min(steps) > 1e-9
    start = ctx.port_pins['motion_J5']['pins'][str(pin)]
    angle = math.radians(row['azimuth_deg'])
    radial = np.array([math.cos(angle), math.sin(angle), 0.])
    end = radial * 29.6 + [0., 0., 168.]
    assert np.linalg.norm(p[0] - start) < 1e-8
    assert np.linalg.norm(p[-1] - end) < 1e-8
    assert np.linalg.norm(p[100] - start - [0., 0., 5.]) < 1e-8
    assert np.allclose(p[:101, :2], start[:2])
    hit_root = ctx.clear(p[:101], ignore={'Plug_motion_J5'})
    hit_remainder = ctx.clear(p[100:], error)

    # A join error or cusp would invalidate the analytic per-arc radius claim.
    a, b, c = p[:-2], p[1:-1], p[2:]
    ab, bc, ac = b-a, c-b, c-a
    cross = np.linalg.norm(np.cross(ab, bc), axis=1)
    curved = cross > 1e-12
    radii = (np.linalg.norm(ab, axis=1)[curved] *
             np.linalg.norm(bc, axis=1)[curved] *
             np.linalg.norm(ac, axis=1)[curved] / (2*cross[curved]))
    minimum = float(radii.min())
    polygon_length = float(steps.sum())
    assert minimum >= 6.9342, (pin, minimum)
    assert 0 <= row['analytic_body_neck_length_mm']-polygon_length < .02
    checks.append(dict(pin=pin, status='FAIL' if hit_root or hit_remainder else 'PASS',
        root_exception='Own mating housing only, first straight 5 mm; every other target checked',
        root_hit=hit_root, remainder_hit=hit_remainder,
        source_start_mm=start.tolist(), neck_end_mm=end.tolist(),
        source_pin_identity_preserved=True,
        minimum_three_point_radius_mm=minimum,
        analytic_minimum_radius_mm=row['minimum_curvature_radius_mm'],
        analytic_length_mm=row['analytic_body_neck_length_mm'],
        polygon_length_mm=polygon_length, polygon_chord_error_bound_mm=error,
        maximum_sample_step_mm=float(steps.max())))
    bounds[pin] = radius+gap+float(steps.max())/2+error+1e-4

moving = {n:s for n,s in ctx.ss.items() if s.group in ['yaw','pitch']}
corners = {n:np.array(list(itertools.product(*zip(s.lo,s.hi)))) for n,s in moving.items()}
allpoints = np.vstack(list(paths.values()))
lo = allpoints.min(0)-max(bounds.values())
hi = allpoints.max(0)+max(bounds.values())

def clearance(p, solid, bound):
    ids = np.flatnonzero(np.all(p >= solid.lo-bound,axis=1) &
                         np.all(p <= solid.hi+bound,axis=1))
    tree = solid.bvh()
    for i in ids:
        distance = float(tree.find_nearest(Vector(p[i]))[3])
        if distance < bound:
            return dict(part=solid.name, point_mm=p[i].tolist(),
                        distance_mm=distance, required_bound_mm=bound)
    starts = ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
    for i in starts:
        v = p[i]
        if np.all(v>=solid.lo) and np.all(v<=solid.hi):
            probe=manifold.Manifold.sphere(.005,12).translate(v.tolist())
            if (probe ^ solid.m).volume() > probe.volume()/2:
                return dict(part=solid.name,point_mm=v.tolist(),inside=True)
    return None

poses=[]
examined=set()
for yaw in range(-60,61,10):
    for pitch in range(-20,26,5):
        tr = {g:rigidtr(yaw,pitch if g=='pitch' else 0) for g in ['yaw','pitch']}
        nearby={}
        for name,s in moving.items():
            t=np.asarray(tr[s.group]); bb=corners[name]@t[:3,:3].T+t[:3,3]
            if np.any(bb.max(0)<lo) or np.any(bb.min(0)>hi):continue
            nearby[name]=Solid(s.o,s,tr[s.group]);examined.add(name)
        bad=[]
        for pin,p in paths.items():
            for name,s in nearby.items():
                hit=clearance(p,s,bounds[pin])
                if hit:bad.append(dict(pin=pin,**hit))
        poses.append(dict(yaw_deg=yaw,pitch_deg=pitch,status='FAIL' if bad else 'PASS',
                          failures=bad,nearby_parts=sorted(nearby)))
    print('PACKED_NATIVE_YAW',yaw,'failed_poses',sum(r['status']=='FAIL' for r in poses),flush=True)

ctx.assert_unchanged()
failures=[r for r in poses if r['status']=='FAIL']
result=dict(status='FAIL' if failures or any(r['status']=='FAIL' for r in checks) else 'PASS',
    scope='Four connected fixed J5-to-neck curves with 252 zero-pose targets and 130 native head poses',
    **ctx.evidence(),script_sha256=sha(__file__),selection_sha256=sha(selection_path),
    selected_curves_sha256=sha(curve_path),zero_pose_checks=checks,
    zero_pose_target_count=len(ctx.targets),moving_native_parts=len(moving),
    nearby_moving_parts=sorted(examined),poses=poses,failed_poses=failures,
    interwire_source_sha256=sha(selection_path),wire_OD_mm=2*radius,surface_gap_mm=gap,
    main_unchanged=True,main_applied=False,whole_harness='BLOCKED',
    assembly='NOT_TESTED',upper_service_loop='NOT_TESTED',
    continuous_between_head_poses='NOT_TESTED',supplier_cut_lengths_released=False,
    elapsed_s=time.time()-started)
(HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('PACKED_NATIVE_DONE',result['status'],'poses',len(poses),'failures',len(failures),flush=True)
