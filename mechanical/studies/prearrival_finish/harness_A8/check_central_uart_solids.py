"""Check A8 central four-wire paths against unchanged M1.47 source solids."""
from pathlib import Path
A8_SCRIPT=Path(__file__).resolve()
A8_HELPER=A8_SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(A8_HELPER)
exec(compile(A8_HELPER.read_text().split('\ngroups=[]')[0],str(A8_HELPER),'exec'),globals())
__file__=str(A8_SCRIPT)
from numpy.polynomial import polynomial as poly
OUT=Path(__file__).resolve().parent
path=OUT/'central_uart_curves.json';curves=json.loads(path.read_text())
assert curves['source_blend_sha256']==before
assert curves['status']=='PASS'
radius=curves['wire_od_max_mm']/2
phase_angles=curves['wire_zero_azimuths_deg']
hits=[];fixed_hits=[];pairs=[];self_checks=[];tested=0
solid_meshes={}

def absolute_extremum(co):
    roots=poly.polyroots(poly.polyder(co))
    ts=[0.,1.]+[float(r.real) for r in roots if abs(r.imag)<1e-8 and 0<r.real<1]
    return float(np.abs(poly.polyval(ts,co)).max())

for pose in curves['selected']['poses']:
    yaw=pose['yaw_deg'];base_pts=np.asarray(pose['first_wire_curve_mm'])
    err=pose['second_derivative_chord_error_bound_mm']
    M=absolute_extremum(poly.polyder(pose['angular_polynomial_coefficients']))
    R=curves['radius_from_yaw_axis_mm'];height=np.diff(curves['z_endpoints_mm'])[0]
    # Equal-Z rotational copies: for |dt| >= delta vertical separation alone
    # provides H*delta. Otherwise the circle's angular metric gives this XY
    # bound from the exact max angular derivative. All parameter pairs covered.
    for aa,bb in itertools.combinations(phase_angles,2):
        angle=math.radians(min(abs(bb-aa),360-abs(bb-aa)))
        ds=np.linspace(.001,min(1,angle/max(M,1e-12)),1001)
        bounds=np.minimum(height*ds,2*R*np.sin(np.maximum(0,angle-M*ds)/2))
        bound=float(bounds.max());surface=bound-2*radius
        pairs.append(dict(yaw_deg=yaw,wires=[aa,bb],method='global axial/angular separation bound',
            centre_distance_lower_bound_mm=bound,surface_gap_lower_bound_mm=surface,
            status='PASS' if surface>=.3 else 'FAIL'))
    speedmax=math.sqrt(height*height+(R*M)**2)
    nonlocal_arc_cutoff=math.pi*(radius+.3)
    self_bound=height*nonlocal_arc_cutoff/speedmax
    self_checks.append(dict(yaw_deg=yaw,method='monotone axial displacement and speed bound',
        arc_separation_cutoff_mm=nonlocal_arc_cutoff,nonlocal_distance_lower_bound_mm=self_bound,
        required_envelope_separation_mm=2*(radius+.3),
        status='PASS' if self_bound>=2*(radius+.3) else 'BLOCKED',
        local_curvature='Numerically screened in curve source; not a global curvature proof'))
    for wire_i,phase in enumerate(phase_angles):
        ang=math.radians(phase);rot=np.array([[math.cos(ang),-math.sin(ang),0],[math.sin(ang),math.cos(ang),0],[0,0,1.]])
        pts=base_pts@rot.T
        fh=fixed_clear(pts,radius,err)
        if fh:fixed_hits.append(dict(wire=wire_i+1,yaw_deg=yaw,**fh))
        for pitch in range(-20,26,5):
            tested+=1
            for name,s in ss.items():
                if s.group in ['yaw','pitch']:
                    inv=np.linalg.inv(np.asarray(rigidtr(yaw,pitch if s.group=='pitch' else 0)))
                    local=pts@inv[:3,:3].T+inv[:3,3]
                else:local=pts
                hit=sample_clear(local,radius,err,[name])
                if hit:hits.append(dict(wire=wire_i+1,yaw_deg=yaw,pitch_deg=pitch,**hit))
        print('A8_CENTRAL_SOURCE_WIRE',yaw,wire_i+1,'hits',len(hits),round(time.time()-start,2),flush=True)

# The two existing local loops lie outside this entire annular column.
other_loop_checks=[]
for group in seed['groups']:
    if group['status']!='PASS':continue
    bound=min(group['centre_radius_bounds_mm'])-curves['radius_from_yaw_axis_mm']-radius-group['diameter_mm']/2
    other_loop_checks.append(dict(other=group['id'],method='global disjoint cylindrical radial slabs',
        surface_gap_lower_bound_mm=bound,status='PASS' if bound>=.3 else 'FAIL'))

ok=not hits and not fixed_hits and all(x['status']=='PASS' for x in pairs+self_checks+other_loop_checks)
result=dict(status='PASS' if ok else 'BLOCKED',scope='Central 32 mm-high UART passage only, no terminal approaches or installed harness',
    source_blend_sha256=before,source_curve_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    source_existing_loops_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest(),
    source_fixed_wires_sha256=hashlib.sha256(fixed_path.read_bytes()).hexdigest(),
    source_readonly_helper_sha256=hashlib.sha256(A8_HELPER.read_bytes()).hexdigest(),
    physical_source_objects=len(ss),combined_head_poses=130,wire_pose_instances=tested,
    source_solid_hits=hits,fourteen_fixed_wire_hits=fixed_hits,interwire_checks=pairs,
    nonlocal_self_checks=self_checks,other_loop_checks=other_loop_checks,
    radius_from_axis_mm=curves['radius_from_yaw_axis_mm'],wire_od_max_mm=2*radius,
    minimum_project_source_surface_gap_mm=.3,
    full_eleven_wire_head_harness='BLOCKED',physical_retention='NOT_TESTED',
    assembly_of_wires='NOT_TESTED',dynamic_life='NOT_TESTED',main_geometry_changed=False,
    elapsed_s=time.time()-start,
    limitations=['Original closed mesh proxies and finite 13 yaw by 10 pitch poses only.',
        'Clearance subtracts sample spacing and analytic curve chord-error allowances.',
        'An annular passage is not an installed service loop; physical guides and endpoint approaches are still missing.',
        'No source STEP revision, connector mating or final wire procurement was approved by this study.'])
(OUT/'central_uart_source_check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('A8_CENTRAL_SOURCE_COMPLETE',result['status'],len(hits),len(fixed_hits),round(time.time()-start,2),flush=True)
