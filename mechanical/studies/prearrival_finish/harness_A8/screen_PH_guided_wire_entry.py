"""Screen an alternative PH motion with the four free tails outside the neck.

A tangent circular/straight guide defines both the changing PH orientation and
four parallel-transported wires. Five straight millimetres remain at the plug.
All nominal wire material is represented; neck threading is a later, unresolved
operation. This candidate changes no production files or printed parts.
"""
from pathlib import Path

GUIDED_SCRIPT = Path(__file__).resolve()
GUIDED_HELPER = GUIDED_SCRIPT.parent / 'screen_CAM_PH_attached_wire_entry.py'
__file__ = str(GUIDED_HELPER)
exec(compile(GUIDED_HELPER.read_text().split('\nstarted = time.time()', 1)[0],
             str(GUIDED_HELPER), 'exec'), globals())
__file__ = str(GUIDED_SCRIPT)
OUT = STOCK_OUT / 'PH_guided_wire_entry'
OUT.mkdir(exist_ok=True)
native_root = np.mean(np.array(list(native_exits.values())), axis=0)
slot_offsets = [-3., -1., 1., 3.]


def rotate(v, axis, angle):
    return v*math.cos(angle) + np.cross(axis, v)*math.sin(angle) + axis*np.dot(axis, v)*(1-math.cos(angle))


def make_guide(parameters):
    radius, height, x_shift, early_y, rise = parameters
    points = native_root + np.array([[0,0,5], [0,0,height], [-x_shift,0,height],
        [-x_shift,early_y,height+rise], [-x_shift,44,height+rise], [-x_shift,44,85.]])
    corners = []
    for a, b, c in zip(points[:-2], points[1:-1], points[2:]):
        vin, vout = b-a, c-b
        vin /= np.linalg.norm(vin)
        vout /= np.linalg.norm(vout)
        angle = math.acos(float(np.clip(np.dot(vin, vout), -1., 1.)))
        axis = np.cross(vin, vout)
        axis /= np.linalg.norm(axis)
        setback = radius*math.tan(angle/2)
        entry, end = b-vin*setback, b+vout*setback
        center_arc = entry+radius*np.cross(axis, vin)
        assert np.linalg.norm(center_arc+rotate(entry-center_arc, axis, angle)-end) < 1e-8
        corners.append(dict(entry=entry, end=end, axis=axis, angle=angle, radius=radius,
                            c=center_arc, r0=entry-center_arc, tangent=vin))
    segments = []
    cursor = points[0]
    normal = np.array([1.,0.,0.])
    tangent = np.array([0.,0.,1.])
    for corner in corners:
        delta = corner['entry']-cursor
        distance = float(np.linalg.norm(delta))
        if np.dot(delta, tangent) < -1e-8:
            return None, dict(kind='overlapping_corner_setbacks')
        if distance > 1e-8:
            assert np.linalg.norm(delta/distance-tangent) < 1e-8
            segments.append(dict(kind='line', start=cursor.copy(), end=corner['entry'].copy(),
                length=distance, tangent=tangent.copy(), normal=normal.copy()))
        segments.append(dict(kind='arc', length=radius*corner['angle'], normal=normal.copy(), **corner))
        normal = rotate(normal, corner['axis'], corner['angle'])
        tangent = rotate(tangent, corner['axis'], corner['angle'])
        cursor = corner['end']
    delta = points[-1]-cursor
    distance = float(np.linalg.norm(delta))
    if np.dot(delta,tangent) < 0:
        return None, dict(kind='negative_final_straight')
    assert np.linalg.norm(delta/distance-tangent) < 1e-8
    segments.append(dict(kind='line', start=cursor.copy(), end=points[-1], length=distance,
                         tangent=tangent.copy(), normal=normal.copy()))
    s = 0.
    for segment in segments:
        segment['s0'], segment['s1'] = s, s+segment['length']
        s += segment['length']
    return dict(segments=segments, length=s, parameters=parameters), None


def segment_pose(segment, s):
    local = max(0., min(segment['length'], s-segment['s0']))
    if segment['kind'] == 'line':
        return segment['start']+local*segment['tangent'], segment['tangent'], segment['normal']
    angle = local/segment['radius']
    return (segment['c']+rotate(segment['r0'],segment['axis'],angle),
            rotate(segment['tangent'],segment['axis'],angle),
            rotate(segment['normal'],segment['axis'],angle))


def guide_pose(guide, s):
    segment = next((q for q in guide['segments'] if q['s1'] >= s-1e-9), guide['segments'][-1])
    return segment_pose(segment, s)


def guided_wire(guide, s, pin):
    offset = slot_offsets[pin-1]
    p, tangent, normal = guide_pose(guide, s)
    start = p+offset*normal
    pieces = [line(start-5*tangent,start)]
    analytic = 5.
    error = 0.
    minimum_radius = float('inf')
    for segment in guide['segments']:
        if segment['s1'] <= s+1e-9:
            continue
        s0 = max(s, segment['s0'])
        sample = np.linspace(s0, segment['s1'], max(2,math.ceil((segment['s1']-s0)/.10)+1))
        placed_points = []
        for u in sample:
            c,t,n = segment_pose(segment,float(u))
            placed_points.append(c+offset*n)
        pieces.append(np.array(placed_points)[1:])
        if segment['kind'] == 'line':
            analytic += segment['s1']-s0
        else:
            radial = segment['r0']/segment['radius']
            actual_radius = segment['radius']+offset*float(np.dot(segment['normal'],radial))
            minimum_radius = min(minimum_radius, actual_radius)
            angle = (segment['s1']-s0)/segment['radius']
            analytic += actual_radius*angle
            error = max(error, actual_radius*(1-math.cos(angle/(len(sample)-1)/2)))
    prefix = np.vstack(pieces)
    stock = lengths[pin-1]['full_nominal_allocation_mm']-analytic
    if stock < 5.:
        return None,dict(kind='insufficient_free_end_stock',pin=pin,stock_mm=stock)
    p,t,n = guide_pose(guide,guide['length'])
    assert np.linalg.norm(t-[0,0,1])<1e-8
    terminal_origin = p+offset*n
    # At the last guide sample only the five-millimetre exit is left.
    assert np.linalg.norm(prefix[-1]-terminal_origin)<1e-8
    full = np.vstack([prefix,line(terminal_origin,terminal_origin+[0,0,stock])[1:]])
    if minimum_radius < 7.-1e-8:
        return None,dict(kind='bend_radius',pin=pin,minimum_mm=minimum_radius)
    return dict(points=full,pin=pin,stock_mm=stock,curve_chord_error_mm=error,
        analytic_total_mm=analytic+stock,sampled_total_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
        minimum_analytic_radius_mm=None if math.isinf(minimum_radius) else minimum_radius),None


def guided_housing(guide,s,padded=True):
    p,t,n=guide_pose(guide,s)
    b=np.cross(t,n)
    assert abs(np.linalg.det(np.column_stack([n,b,t]))-1.)<1e-8
    return manifold.Manifold.cube(size+(2*pad if padded else 0),center=True).transform(
        np.column_stack([n,b,t,p-(5+size[2]/2)*t]))


def check_guided_state(guide,s,whole_wires=True):
    posed_housing=guided_housing(guide,s)
    failure=collision(posed_housing,allow_native=s<=8.+1e-8)
    if failure:
        return {},[],dict(failure,stage='guided_PH_obstacle')
    if not whole_wires:
        return {},[],None
    curves={}
    for pin in range(1,5):
        curve,failure=guided_wire(guide,s,pin)
        if failure:return curves,[],failure
        curves[pin]=curve
        lengths[pin-1]['curve_chord_error_mm']=curve['curve_chord_error_mm']
        failure=wire_check(pin,curve['points'],identity_matrices) or self_check(curve)
        if not failure:failure=rigid_check(make_terminal(curve,I),identity_matrices)
        if failure:return curves,[],failure
    pairs,failure=mutual_check(curves)
    if not failure:failure=terminal_checks(curves,I)
    return curves,pairs,failure


started=time.time(); trials=[];saved={};selected_guide=None
# Start with a long rear rise and broad tangential bends. Vary only these
# declared guide parameters; no collision body, margin or wire radius is reduced.
parameter_cases=itertools.product([12.,11.,10.5], [34.,32.,36.,30.,38.], [26.,28.,24.,30.],
                                 [16.,20.,12.,24.], [10.,8.,12.])
for candidate,parameters in enumerate(parameter_cases):
    guide,failure=make_guide(list(parameters))
    rows=[]
    if not failure:
        curves,pairs,failure=check_guided_state(guide,0.)
        rows.append(dict(s_mm=0.,status='BLOCKED' if failure else 'PASS',failure=failure,pairs=pairs))
        if not failure:
            critical=sorted(set([q['s0'] for q in guide['segments']]+[q['s1'] for q in guide['segments']]))
            # Endpoints and midpoints expose geometric failures before a dense replay.
            sample=sorted(set(critical+[(a+b)/2 for a,b in zip(critical[:-1],critical[1:])]))
            for s in sample[1:]:
                _,_,failure=check_guided_state(guide,s,whole_wires=False)
                rows.append(dict(s_mm=s,status='BLOCKED' if failure else 'PASS',failure=failure))
                if failure:break
    trials.append(dict(candidate=candidate,parameters=list(parameters),status='BLOCKED' if failure else 'PASS',
                       failure=failure,rows=rows))
    if candidate%40==0 or failure is None:
        print('PH_GUIDE_TRIAL',candidate,list(parameters),'BLOCKED' if failure else 'PASS',failure,
              round(time.time()-started,2),flush=True)
    if failure is None:
        selected_guide=guide
        break
    if time.time()-started>180.:
        break

replay=[]
if selected_guide:
    n=math.ceil(selected_guide['length']/.75)
    previous={}
    for index,s in enumerate(np.linspace(0.,selected_guide['length'],n+1)):
        curves,pairs,failure=check_guided_state(selected_guide,float(s))
        for pin,c in curves.items():saved[f'pose{index}_pin{pin}']=c['points']
        row=dict(index=index,s_mm=float(s),status='BLOCKED' if failure else 'PASS',failure=failure,pairs=pairs,
            curves=[{k:v for k,v in c.items() if k!='points'} for c in curves.values()])
        replay.append(row)
        if index%20==0 or failure:
            print('PH_GUIDE_REPLAY',index,len(replay),'BLOCKED' if failure else 'PASS',failure,flush=True)
        if failure:break

np.savez_compressed(OUT/'curves.npz',**saved)
serial_guide=None
if selected_guide:
    serial_guide=dict(parameters=selected_guide['parameters'],length=selected_guide['length'],
        segments=[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in q.items()} for q in selected_guide['segments']])
status='PASS' if replay and not replay[-1]['failure'] and abs(replay[-1]['s_mm']-selected_guide['length'])<1e-8 else 'BLOCKED'
report=dict(status=status,scope='Finite new free-tail PH assembly candidate; neck feed follows later',
    script_sha256=sha(GUIDED_SCRIPT),helper_sha256=sha(GUIDED_HELPER),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [ph_path,pack_path,joined_path,partial_path,datum_path,
        body_math_path,JOINT_DATA,JOINT_REPORT,curve_helper,self_helper,terminal_helper]},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_target_members=sorted(targets),wire_OD_mm=OD,clearance_mm=MARGIN,first_straight_mm=5.,
    original_nominal_lengths_mm=[r['full_nominal_allocation_mm'] for r in lengths],
    trials=trials,selected_guide=serial_guide,replay=replay,curves_sha256=sha(OUT/'curves.npz'),
    continuous_motion='NOT_TESTED',own_housing_nonlocal_wire_clearance='NOT_TESTED',
    subsequent_neck_threading='NOT_TESTED',later_H01_H04_installation='NOT_TESTED',
    hands_and_tools='NOT_TESTED',actual_terminal_and_wire='NOT_TESTED',
    complete_attached_assembly='BLOCKED',main_applied=False,manufacturing_release=False,
    elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('PH_GUIDE_DONE',status,len(trials),len(replay),round(time.time()-started,2),flush=True)
