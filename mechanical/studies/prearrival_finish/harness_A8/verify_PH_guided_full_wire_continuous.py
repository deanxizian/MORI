"""Cover complete analytic CAM wires over the guided PH candidate continuously.

The remaining guide is a nested subset of a fixed four-wire curve. End stock is
vertical and grows monotonically. Only each five-millimetre leading straight
and PH housing move outside that set. These have conservative rotational bounds.
"""
from pathlib import Path

FULL_GUIDE_SCRIPT=Path(__file__).resolve()
FULL_GUIDE_HELPER=FULL_GUIDE_SCRIPT.parent/'verify_PH_guided_wire_entry.py'
__file__=str(FULL_GUIDE_HELPER)
exec(compile(FULL_GUIDE_HELPER.read_text().split('\nstarted=time.time();',1)[0],
             str(FULL_GUIDE_HELPER),'exec'),globals())
__file__=str(FULL_GUIDE_SCRIPT)
verified=json.loads((OUT/'verification.json').read_text())
assert verified['status']=='PASS' and verified['script_sha256']==sha(FULL_GUIDE_HELPER)
assert verified['source_report_sha256']==sha(OUT/'screen.json')


def remaining_envelope(s,pin,skip_after_join=0.):
    curve,failure=guided_wire(guide,s,pin)
    assert failure is None
    # Use a union envelope for all possible later tail positions; this does
    # not add material to the actual constant-length candidate.
    points=curve['points']
    distances=np.r_[0.,np.linalg.norm(np.diff(points,axis=0),axis=1).cumsum()]
    points=points[distances>=5.+skip_after_join-1e-8]
    end,_,normal=guide_pose(guide,guide['length'])
    max_endpoint=end+slot_offsets[pin-1]*normal+[0,0,lengths[pin-1]['full_nominal_allocation_mm']-5.]
    assert max_endpoint[2]>=points[-1,2]-1e-8
    points=np.vstack([points,line(points[-1],max_endpoint)[1:]])
    return dict(curve,points=points)


def shape_against_curve(shape,curve):
    mesh=shape.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);f=np.asarray(mesh.tri_verts)
    lo,hi=v.min(0),v.max(0)
    tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
    points=curve['points'];step=float(np.linalg.norm(np.diff(points,axis=0),axis=1).max())
    allowance=OD/2+curve['curve_chord_error_mm']+step/2+1e-4
    indices=np.flatnonzero(np.all(points>=lo-allowance,axis=1)&np.all(points<=hi+allowance,axis=1))
    for index in indices:
        q=points[index]
        distance=float(tree.find_nearest(Vector(q))[3])
        if distance<allowance:
            return dict(kind='wire_near_continuous_bound',point_mm=q.tolist(),pin=curve['pin'],
                        distance_mm=distance,required_bound_mm=allowance)
    # After the boundary-distance bound, no connected sample run can cross
    # the solid unseen. Test each run's first point for closed-solid containment.
    # This avoids relying on normals of extremely small Minkowski-hull faces.
    starts=indices[np.r_[True,np.diff(indices)>1]] if len(indices) else []
    for index in starts:
        q=points[index]
        if np.all(q>=lo) and np.all(q<=hi):
            probe=manifold.Manifold.sphere(.005,12).translate(q.tolist())
            if (probe^shape).volume()>probe.volume()/2:
                return dict(kind='wire_inside_continuous_bound',point_mm=q.tolist(),pin=curve['pin'])
    return None


started=time.time();failure=None;union_curves={}
for pin in range(1,5):
    c=remaining_envelope(0.,pin)
    union_curves[pin]=c
    lengths[pin-1]['curve_chord_error_mm']=c['curve_chord_error_mm']
    failure=wire_check(pin,c['points'],identity_matrices) or self_check(c)
    if failure:break
union_pairs=[]
if not failure:union_pairs,failure=mutual_check(union_curves)
union_status='BLOCKED' if failure else 'PASS'
print('GUIDE_STATIC_UNION',union_status,failure,flush=True)

# In every actual pose each leading straight is parallel to its neighbours.
lead_pair_gap=min(abs(a-b) for a,b in itertools.combinations(slot_offsets,2))-OD
assert lead_pair_gap>=MARGIN
# For a C1 curve with curvature <= 1/R, a subarc of length l <= pi*R
# projects onto its midpoint tangent with length >= 2R*sin(l/(2R)).
# The first 10 mm after the join plus the 5 mm straight has l <= 15 mm.
# For nonlocal pairs l >= 2 mm this bound is already above OD+clearance.
minimum_radius=min(q['radius']-max(abs(x) for x in slot_offsets) for q in guide['segments'] if q['kind']=='arc')
assert minimum_radius>=7. and 15.<math.pi*minimum_radius
local_self_lower=2*minimum_radius*math.sin(2./(2*minimum_radius))
assert local_self_lower>OD+MARGIN

intervals=[]
if not failure:
    for primitive_index,segment in enumerate(guide['segments']):
        samples=np.linspace(segment['s0'],segment['s1'],max(2,math.ceil(segment['length']/.75)+1))
        for a,b in zip(samples[:-1],samples[1:]):
            remaining={pin:remaining_envelope(float(a),pin) for pin in range(1,5)}
            nonlocal_self={pin:remaining_envelope(float(a),pin,10.) for pin in range(1,5)}
            row=dict(primitive=primitive_index,a_mm=float(a),b_mm=float(b),checks=0)
            for item in ['PH',1,2,3,4]:
                left=guided_housing(guide,float(a)) if item=='PH' else lead_box(float(a),item)
                right=guided_housing(guide,float(b)) if item=='PH' else lead_box(float(b),item)
                bound,error=continuous_bound(segment,float(a),float(b),left,right)
                for pin in range(1,5):
                    c=nonlocal_self[pin] if item==pin else remaining[pin]
                    failure=shape_against_curve(bound,c)
                    row['checks']+=1
                    if failure:
                        failure.update(moving_item=item,primitive=primitive_index,a_mm=float(a),b_mm=float(b),
                                       rotational_bound_error_mm=error)
                        break
                if failure:break
            row.update(status='BLOCKED' if failure else 'PASS',failure=failure)
            intervals.append(row)
            if failure:break
        print('GUIDE_FULL_INTERVAL',primitive_index,len(intervals),'BLOCKED' if failure else 'PASS',failure,flush=True)
        if failure:break

terminal_rows=[];terminal_motion=[]
if not failure:
    for pin in range(1,5):
        ca,err=guided_wire(guide,0.,pin);assert err is None
        cb,err=guided_wire(guide,guide['length'],pin);assert err is None
        first,last=make_terminal(ca,I),make_terminal(cb,I)
        sweep=manifold.Manifold.batch_hull([first,last])
        failure=rigid_check(sweep,identity_matrices)
        if not failure:
            for other,c in union_curves.items():
                if pin==other:continue
                failure=shape_against_curve(sweep,c)
                if failure:break
        terminal_motion.append(dict(pin=pin,status='BLOCKED' if failure else 'PASS',failure=failure))
        if failure:break
if not failure:
    for primitive_index,segment in enumerate(guide['segments']):
        endpoints={}
        for s in [segment['s0'],segment['s1']]:
            curves={}
            for pin in range(1,5):
                curve,err=guided_wire(guide,s,pin);assert err is None
                curves[pin]=curve
            endpoints[s]=curves
        for a,b in itertools.combinations(range(1,5),2):
            ca0,cb0=endpoints[segment['s0']][a],endpoints[segment['s0']][b]
            ca1,cb1=endpoints[segment['s1']][a],endpoints[segment['s1']][b]
            # Stock differences are linear on every straight/circular primitive.
            # Subtract the motion of terminal b before taking a's endpoint hull.
            delta_b=cb1['points'][-1]-cb0['points'][-1]
            sweep=manifold.Manifold.batch_hull([make_terminal(ca0,I),make_terminal(ca1,I).translate((-delta_b).tolist())])
            volume=max(0.,float((sweep^make_terminal(cb0,I)).volume()))
            if volume>1e-5:failure=dict(kind='relative_terminal_overlap',a=a,b=b,primitive=primitive_index,volume_mm3=volume)
            terminal_rows.append(dict(primitive=primitive_index,a=a,b=b,intersection_mm3=volume,
                                      status='BLOCKED' if failure else 'PASS'))
            if failure:break
        if failure:break

report=dict(status='BLOCKED' if failure else 'PASS',
    scope='Continuous geometry of four constant-length analytic CAM wires for guided PH movement only',
    script_sha256=sha(FULL_GUIDE_SCRIPT),helper_sha256=sha(FULL_GUIDE_HELPER),
    source_verification_sha256=sha(OUT/'verification.json'),source_report_sha256=sha(OUT/'screen.json'),
    source_curves_sha256=sha(OUT/'curves.npz'),protected_sources=protected,source_files=source_report['source_files'],
    static_union_status=union_status,static_union_pairs=union_pairs,
    static_union_is_validation_superset_not_additional_wire=True,
    nominal_lengths_mm=[r['full_nominal_allocation_mm'] for r in lengths],
    continuous_guide_intervals=len(intervals),intervals=intervals,failure=failure,
    moving_leads_analytic_pair_gap_mm=lead_pair_gap,minimum_radius_bound_mm=minimum_radius,
    self_local_exclusion_mm=2.,local_self_curve_length_range_mm=[2.,15.],
    local_self_centerline_lower_bound_mm=local_self_lower,guide_self_local_geometric_check_skipped_mm=10.,
    terminal_motion=terminal_motion,terminal_pair_intervals=terminal_rows,
    PH_and_first5_continuous_sweeps=verified['continuous_sweeps'],
    native_PH_mating_fit='NOT_TESTED',free_terminal_shape_evidence='ASSUMED envelope',
    subsequent_neck_threading='NOT_TESTED',later_H01_H04_installation='NOT_TESTED',
    complete_attached_assembly='BLOCKED',hands_and_tools='NOT_TESTED',
    main_applied=False,manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'full_wire_continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('GUIDE_FULL_CONTINUOUS_DONE',report['status'],len(intervals),len(terminal_rows),round(time.time()-started,2),failure,flush=True)
