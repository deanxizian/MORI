"""Wider read-only throat screening after the recorded narrow family failed.

Round probes are planning allocations, not selected bundles or cable models.
No candidate geometry is added to, or saved over, the robot.
"""
from pathlib import Path
HELPER = Path(__file__).resolve().with_name('check_outer_neck_probes.py')
exec(compile(HELPER.read_text().split('# Endpoints are named')[0], str(HELPER), 'exec'), globals())
examples = []
TURN = '--turn' in sys.argv

def checked_curve(c, diameter):
    if radius_at_samples(c) < R: return 'bend_radius', None
    rr, _ = extrema_radius(c)
    if rr < R: return 'bend_radius_extrema', None
    points = bezier(c, grid_t)
    why = screen(points, diameter / 2)
    if why:
        if len(examples) < 12:
            s = obstacles[why]; ch = float(np.max(np.linalg.norm(np.diff(points, axis=0), axis=1)))
            dist = [(trees[why].find_nearest(Vector(p))[3], p.tolist()) for p in points]
            dd, pp = min(dist)
            examples.append(dict(diameter_mm=diameter, controls=c.tolist(), blocker=why,
                nearest_distance_mm=dd, nearest_path_point_mm=pp, screen_clearance_mm=diameter / 2 + gap + ch / 2 + .001))
        return why, None
    return None, dict(probe_diameter_mm=diameter, curve_mm=points.tolist(), cubic_controls_mm=c.tolist(),
        minimum_curvature_radius_mm=rr, geometric_length_mm=float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum()),
        maximum_chord_mm=float(np.max(np.linalg.norm(np.diff(points, axis=0), axis=1))))

for diameter in [6., 5., 4., 3.]:
    candidates = []
    # The previous narrow family constrained both end slopes. Here the two
    # intermediate control points are separate staging allocations instead.
    family = ([-47.,-45.,-43.,-41.], [-28.,-25.,-22.], [-49.,-47.,-45.,-43.],
        [-40.,-36.,-32.], [154.,158.,162.,166.], [172.,174.,176.]) if TURN else (
        [-49., -46., -43., -40.], [-32., -29., -26., -23.],
        [-46., -42., -38.], [-40., -36., -32.], [146., 151.], [162., 168.])
    for sy, ey, cy1, cy2, z1, z2 in itertools.product(*family):
        tried += 1
        c = np.array([[0., sy, 140.], [0., cy1, z1], [0., cy2, z2], [0., ey, 174. if TURN else 176.]])
        why, row = checked_curve(c, diameter)
        if why: reasons[why] += 1
        else: candidates.append(row)
    if candidates: valid.append(min(candidates, key=lambda row: row['geometric_length_mm']))
    print('WIDE_NECK_POOL', diameter, len(candidates), time.time()-start, flush=True)

checks = []
for row in valid:
    points = np.asarray(row['curve_mm']); radius = row['probe_diameter_mm']/2 + gap
    # Circumscribe both cylinders and sphere approximations. For a sphere
    #32 mesh, measure its actual face-plane inradius instead of assuming it.
    unit = manifold.Manifold.sphere(1, 32); mesh = unit.to_mesh64()
    verts = np.asarray(mesh.vert_properties[:, :3]); tri = verts[np.asarray(mesh.tri_verts)]
    normals = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); normals /= np.linalg.norm(normals,axis=1)[:,None]
    inradius = float(np.min(np.abs(np.sum(normals*tri[:,0],axis=1))))
    # Bound the distance between each cubic subarc and its chord from the
    # maximum second derivative, ||f''||*dt^2/8, valid for cubic coordinates.
    c = np.asarray(row['cubic_controls_mm']); second = 6*np.array([c[2]-2*c[1]+c[0],c[3]-2*c[2]+c[1]])
    chord_error = float(np.linalg.norm(second,axis=1).max()/((len(points)-1)**2*8))
    inflated = radius + chord_error + 1e-4
    pieces = [unit.scale([inflated/inradius]*3).translate(p.tolist()) for p in points]
    for a,b in zip(points,points[1:]):
        delta=b-a; length=np.linalg.norm(delta)
        pieces.append(axial(inflated/math.cos(math.pi/64),length,(a+b)/2,delta/length,segments=64))
    m = manifold.Manifold.batch_boolean(pieces,manifold.OpType.Add); bb=np.asarray(m.bounding_box())
    hits=[]; motion=[]
    for name,s in ss.items():
        if np.any(bb[:3]>s.hi) or np.any(bb[3:]<s.lo): continue
        v=max(0.,(m^s.m).volume())
        if v>.001:hits.append(dict(object=name,volume_mm3=v))
    for yaw in range(-60,61,10):
        for pitch in range(-20,26,5):
            for name,s in ss.items():
                if s.group not in ['yaw','pitch']: continue
                other=s.m.transform(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0))[:3,:]); ob=np.asarray(other.bounding_box())
                if np.any(bb[:3]>ob[3:]) or np.any(bb[3:]<ob[:3]): continue
                v=max(0.,(m^other).volume())
                if v>.001:motion.append(dict(object=name,yaw_deg=yaw,pitch_deg=pitch,volume_mm3=v))
    checks.append(dict(diameter_mm=row['probe_diameter_mm'],static_status='FAIL' if hits else 'PASS',
        fixed_occupancy_motion_status='FAIL' if motion else 'PASS',static_hits=hits,motion_hits=motion,
        head_pose_count=130, curved_to_polyline_error_bound_mm=chord_error,sphere_unit_inradius=inradius,
        envelope_status=str(m.status()),envelope_volume_mm3=m.volume(),
        scope='Fixed body probe occupancy only, not an attached moving cable or service loop'))
    print('WIDE_NECK_SOLID',row['probe_diameter_mm'],len(hits),len(motion),flush=True)

out=dict(revision=P['revision'],source_blend_sha256=before,
    source_helpers={str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [HELPER,src,wire_path]},
    status='PASS' if checks and all(c['static_status']=='PASS' and c['fixed_occupancy_motion_status']=='PASS' for c in checks) else 'BLOCKED',
    scope='Finite lower-neck staging-to-staging occupancy only; no complete harness claim',
    minimum_static_curve_radius_mm=R,planning_diameters_mm=[6,5,4,3],selected_bundle=False,
    project_gap_per_side_mm=gap,search_cases=tried,rejections=dict(reasons),diagnostic_examples=examples,
    selected=valid,solid_checks=checks,elapsed_s=time.time()-start,main_geometry_changed=False,
    actual_cable_route='NOT_TESTED',anchors='NOT_TESTED',service_loop='NOT_TESTED',
    limitations=['Curve endpoints and diameter are study allocations, not selected supplier datums.',
        'Static source bend radius does not qualify dynamic service life.',
        'No attached endpoint, anchor, bundle packing, lower-body connection or assembly path checked.',
        'No passing curve in this finite family would not prove no other route exists.'])
(HERE/('outer_neck_turn.json' if TURN else 'outer_neck_wide.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('WIDE_NECK_COMPLETE',out['status'],len(checks),time.time()-start,flush=True)
