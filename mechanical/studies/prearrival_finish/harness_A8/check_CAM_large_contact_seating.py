"""Continuous root seating with the same larger contact space as upper feed.

The unchanged wire/structure and wire/wire results are reused by hash.
All contact checks are repeated. Contact X slabs remain disjoint throughout
the motion; touching the plane between adjacent slabs is not physical margin.
"""
from pathlib import Path
LS_SCRIPT=Path(__file__).resolve();LS_ROOT=LS_SCRIPT.parent
LS_HELPER=LS_ROOT/'check_CAM_root_seating_continuous.py';__file__=str(LS_HELPER)
exec(compile(LS_HELPER.read_text().split('\nrc_interval(0.,1.5)',1)[0],str(LS_HELPER),'exec'),globals())
__file__=str(LS_SCRIPT)
LS_OUT=RS_OUT/'large_contact_downstream';LS_OUT.mkdir(exist_ok=True)
ls_source=RX_OUT/'continuous.json';ls_old=json.loads(ls_source.read_text())
assert ls_old['status']=='PASS' and ls_old['complete_coverage'] and not ls_old['unproved_intervals']
assert ls_old['source_main_sha256']==source_hash and ls_old['script_sha256']==sha(LS_HELPER)
assert ls_old['source_math_sha256']==sha(rc_math_file) and ls_old['source_finite_sha256']==sha(rc_finite_file)
ft_dims=np.array([1.,1.8,4.1]);ft_box=manifold.Manifold.cube(ft_dims,center=True);st_angle_max=0.
assert np.allclose(ft_frame(0.,np.zeros(3))[0],np.eye(3),atol=1e-12)
ls_started=time.time();ls_pass=[];ls_unproved=[];ls_tests=0
ls_saved=np.load(RX_OUT/'curves.npz');ls_boundary_error=0.
for offset in (0.,.75,1.5):
    curves,_=rs_curves(offset)
    for slot,q in enumerate(curves):
        ls_boundary_error=max(ls_boundary_error,float(np.linalg.norm(q-ls_saved[f'offset{offset:g}_slot{slot}'],axis=1).max()))
assert ls_boundary_error<1e-9
ls_x=[float(q[-1,0]) for q in curves]
assert all(ls_x[b]-ls_x[a]>=float(ft_dims[0])-1e-10 for a,b in zip(range(3),range(1,4)))


def ls_test(a,b):
    mid=(a+b)/2.;temporal=rc_L*(b-a)/2.
    if temporal>.014:return dict(kind='bound_too_wide',temporal_mm=temporal)
    curves,info=rs_curves(mid)
    errors=[r['curve_error_bound_mm']+r['length_compensation_bound_mm'] for r in info]
    contacts=[]
    for slot,p in enumerate(curves):
        assert abs(p[-1,0]-ls_x[slot])<1e-10
        _,transform=ft_frame(0.,p[-1])
        contacts.append(pw_obstacle(f'allocated_root_contact_{slot}','moving',ft_box.transform(transform)))
    for slot,contact in enumerate(contacts):
        m=contact[2];bounds=np.array(m.bounding_box());needed=.3+temporal+1e-4
        for name,_,solid,lower,upper,_ in rs_targets:
            if np.any(bounds[:3]>upper+needed) or np.any(bounds[3:]<lower-needed):continue
            volume=max(0.,float((m^solid).volume()));gap=float(m.min_gap(solid,needed+.001))
            if volume>1e-7 or gap<needed:
                return dict(kind='contact_structure',slot=slot,object=name,gap_mm=gap,required_mm=needed,intersection_mm3=volume)
        for other,q in enumerate(curves):
            if other==slot:
                boundary=q[-1].copy();boundary[2]-=2.
                q=np.vstack([q[q[:,2]<boundary[2]-1e-10],boundary])
            hit=fc_wire_check(q,errors[other],np.full(len(q),2.*temporal),contact,0.)
            if hit:return dict(kind='contact_wire',slot=slot,other_slot=other,detail=hit)
            q=body_samples[other+1,0][0]
            hit=fc_wire_check(q,body_error,np.full(len(q),temporal),contact,0.)
            if hit:return dict(kind='contact_body',slot=slot,other_slot=other,detail=hit)
        for other in range(slot+1,4):
            # Whole-family proof: orientation is identity and X centre is
            # constant. Independent Y/Z shifts cannot cross disjoint X slabs.
            assert ls_x[other]-ls_x[slot]>=ft_dims[0]-1e-10
            volume=max(0.,float((m^contacts[other][2]).volume()))
            if volume>1e-7:return dict(kind='contact_contact_numeric_regression',slot=slot,other_slot=other,intersection_mm3=volume)
    return None


def ls_interval(a,b,depth=0):
    global ls_tests
    ls_tests+=1;failure=ls_test(a,b)
    if failure is None:
        ls_pass.append(dict(offset_interval_mm=[a,b],status='PASS',contact_displacement_bound_mm=rc_L*(b-a)/2.))
        return
    if depth>=15:
        ls_unproved.append(dict(offset_interval_mm=[a,b],failure=failure));return
    mid=(a+b)/2.;ls_interval(a,mid,depth+1);ls_interval(mid,b,depth+1)


ls_interval(0.,1.5)
ls_pass.sort(key=lambda r:r['offset_interval_mm'][0])
covered=bool(ls_pass and ls_pass[0]['offset_interval_mm'][0]==0. and ls_pass[-1]['offset_interval_mm'][1]==1.5
    and all(a['offset_interval_mm'][1]==b['offset_interval_mm'][0] for a,b in zip(ls_pass,ls_pass[1:])))
status='PASS' if covered and not ls_unproved else 'BLOCKED'
report=dict(status=status,scope='Larger ASSUMED contact allocation through continuous root seating only; unchanged wire geometry checked against its prior certificate',
    script_sha256=sha(LS_SCRIPT),helper_sha256=sha(LS_HELPER),source_main_sha256=source_hash,
    source_unchanged_wire_certificate_sha256=sha(ls_source),source_math_sha256=sha(rc_math_file),
    source_curves_sha256=sha(RX_OUT/'curves.npz'),saved_curve_maximum_difference_mm=ls_boundary_error,
    contact_dimensions_mm=ft_dims.tolist(),contact_evidence='ASSUMED requested space; not vendor maximum post-crimp geometry',
    contact_motion_bound_mm_per_mm=rc_L,contact_contact_proof='Constant identity orientation and pairwise disjoint constant-X slabs for every offset in [0,1.5]; numeric midpoint nonintersection also checked',
    contact_X_centres_mm=ls_x,contact_contact_margin_mm=0.,contact_structure_margin_mm=.3,
    own_crimp_exclusion_mm=2.,own_crimp_boundary_inserted=True,complete_coverage=covered,
    passed_intervals=ls_pass,unproved_intervals=ls_unproved,interval_tests=ls_tests,
    forming_motion_for_larger_contacts='BLOCKED',physical_clearance='NOT_TESTED',
    whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,elapsed_s=time.time()-ls_started)
(LS_OUT/'root_continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LARGER_ROOT_CONTINUOUS_DONE',status,len(ls_pass),len(ls_unproved),round(time.time()-ls_started,2),flush=True)
