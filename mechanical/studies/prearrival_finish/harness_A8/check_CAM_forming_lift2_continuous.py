"""Continuous clearance audit of the unchanged +2mm free-end candidate.

Reuse the previously audited integral velocity bound with this candidate's
actual segment lengths. Both ends of the existing five-millimetre wire bed
are explicit material coordinates; no connecting segment is omitted.
"""
from pathlib import Path
L2_SCRIPT=Path(__file__).resolve();L2_ROOT=L2_SCRIPT.parent
L2_HELPER=L2_ROOT/'check_CAM_forming_continuous.py';__file__=str(L2_HELPER)
exec(compile(L2_HELPER.read_text().split('\ntry:\n    fc_interval',1)[0],str(L2_HELPER),'exec'),globals())
__file__=str(L2_SCRIPT)
L2_OUT=FM_OUT/'lifted_end2';l2_source=json.loads((L2_OUT/'screen.json').read_text())
assert l2_source['status']=='PASS' and l2_source['final_plug_lift_mm']==2.
assert l2_source['source_main_sha256']==source_hash
fr_lengths[:]=l2_source['segment_lengths_mm'];fm_lengths[:]=fr_lengths
fm_core_length=l2_source['core_parameter_mm'];fm_tail_parameter=l2_source['tail_parameter_mm']
fc_R=l2_source['upper_radius_mm'];fc_B=float(sum(fr_lengths[:3]));fc_C=float(sum(fr_lengths[:6]))
fc_h0=fr_lengths[0];fc_end=float(sum(fr_lengths));fc_amplitude=l2_source['selected_amplitude_mm']
fc_seat_start,fc_seat_end=l2_source['seat_material_interval_mm']
l2_old_curve=fc_curve


def fc_curve(fraction):
    p,u,error=l2_old_curve(fraction)
    # The original evaluator already inserts the lower contact boundary.
    # Interpolating the upper boundary contributes at most its chord error.
    v=np.sort(np.unique(np.r_[u,fc_seat_end]))
    q=np.column_stack([np.interp(v,u,p[:,i]) for i in range(3)])
    return q,v,2.*error


def fc_test(a,b):
    global fc_min_contact
    f=(a+b)/2.;half=(b-a)/2.;base,u,error=fc_curve(f)
    temporal=fc_speed(u,a,b)*half
    radial=math.hypot(ft_dims[1]/2.,ft_dims[2])
    contact_motion=(float(fc_speed(np.array([fc_end]),a,b)[0])+2.*math.pi*radial)*half
    nearest=2.+contact_motion
    for slot in range(4):
        rear=base[-1]+[xx[slot]-xx[0],0.,0.];rot,tr=ft_frame(f,rear);contact=ft_box.transform(tr)
        for name,group,m,lo,hi,tree in fm_targets:
            bb=np.array(contact.bounding_box());bound=.3+contact_motion+1e-4
            if np.any(bb[:3]>hi+bound) or np.any(bb[3:]<lo-bound):continue
            v=max(0.,float((contact^m).volume()))
            if v>1e-7:return {'kind':'contact','slot':slot,'object':name,'intersection_mm3':v}
            gap=float(contact.min_gap(m,bound+.001))
            if gap<bound:return {'kind':'contact','slot':slot,'object':name,'gap_mm':gap,'required_mm':bound,'temporal_mm':contact_motion}
            nearest=min(nearest,gap-contact_motion)
    fc_min_contact=min(fc_min_contact,nearest)
    for slot in range(4):
        points=base+[xx[slot]-xx[0],0.,0.]
        for target in fc_targets:
            name=target[0]
            if name in fc_root_contacts:pieces=[(u>=4.3-1e-9,.3)]
            elif name=='CAM_bed_only':
                pieces=[(u<=fc_seat_start+1e-9,.3),
                        ((u>=fc_seat_start-1e-9)&(u<=fc_seat_end+1e-9),0.),
                        (u>=fc_seat_end-1e-9,.3)]
            else:pieces=[(np.ones(len(u),bool),.3)]
            for keep,margin in pieces:
                hit=fc_wire_check(points[keep],error,temporal[keep],target,margin)
                if hit:return {'kind':'wire','slot':slot,**hit}
    return None


# Independently generated finite curves must be the same family, including
# the final endpoint shared with the previously checked seating motion.
l2_identity=[]
for f in np.linspace(0.,1.,21):
    p,u,e=fc_curve(float(f));q,v,qe,_=fr_curve(float(f),fc_amplitude)
    interp=np.column_stack([np.interp(v,u,p[:,i]) for i in range(3)])
    delta=float(np.linalg.norm(interp-q,axis=1).max())
    enddelta=float(np.linalg.norm(p[[0,-1]]-q[[0,-1]],axis=1).max())
    assert delta<=e+1e-8 and enddelta<1e-8
    l2_identity.append({'fraction':float(f),'maximum_difference_mm':delta,'allowed_error_mm':e+1e-8,'endpoint_error_mm':enddelta})
last=fc_curve(1.)[0][-1];_,tails,_=bl_curves(2.,0.)
assert np.linalg.norm(last-tails[0][0])<1e-8
fc_started=time.time();fc_tests=0;fc_passed=[];fc_unproved=[]
try:
    fc_interval(0.,1.)
    fc_error=None
except Exception as exc:
    fc_error=repr(exc)
allrows=sorted(fc_passed+fc_unproved,key=lambda r:r['interval'][0])
coverage=bool(allrows and allrows[0]['interval'][0]==0. and allrows[-1]['interval'][1]==1.
    and all(a['interval'][1]==b['interval'][0] for a,b in zip(allrows,allrows[1:])))
report={'status':'PASS' if coverage and not fc_unproved and not fc_error else 'BLOCKED',
    'scope':'Continuous +2mm four-wire forming and nominal bare-contact clearance to stage solids only',
    'source_main_sha256':source_hash,'script_sha256':sha(L2_SCRIPT),'helper_sha256':sha(L2_HELPER),
    'source_finite_screen_sha256':sha(L2_OUT/'screen.json'),
    'source_bound_audit_sha256':sha(FM_OUT/'continuous/math_audit.json'),
    'segment_lengths_mm':fr_lengths,'upper_radius_mm':fc_R,'lower_radius_mm':fc_r,
    'final_plug_lift_mm':2.,'apex_amplitude_mm':fc_amplitude,'seat_material_interval_mm':[fc_seat_start,fc_seat_end],
    'wire_OD_mm':OD,'ordinary_surface_margin_mm':.3,'bed_nonpenetration_margin_mm':0.,
    'wire_parameter_step_mm':fm_step,'curve_identity_checks':l2_identity,
    'complete_coverage':coverage,'passed_intervals':fc_passed,'unproved_intervals':fc_unproved,
    'interval_tests':fc_tests,'error':fc_error,
    'minimum_contact_gap_lower_bound_mm':fc_min_contact,
    'minimum_bed_gap_lower_bound_mm':fc_min_seat_bound if math.isfinite(fc_min_seat_bound) else None,
    'bound_argument':'For fixed material coordinate u, integrate the absolute tangent-angle derivative. Only the upper turn start moves with H=h0+A*sin(pi*f); its bound uses interval minimum H and maximum absolute Hprime. Contact rotation adds2*pi*r. Midpoint displacement plus spatial chord/sample error bounds every point throughout each interval.',
    'contact_shape_evidence':fc_terminal['contact_shape_evidence'],
    'source_contact_pdf_sha256':fc_terminal['contact_source_pdf_sha256'],
    'uninstalled_CAM_board':True,'untightened_tie_final_solids_omitted':sorted(fm_deferred),
    'wire_packing':'NOT_TESTED','terminal_to_housing_insertion':'NOT_TESTED','initial_feed_to_upright_state':'NOT_TESTED',
    'tie_threading_tightening':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED',
    'manufacturing_release':False,'elapsed_s':time.time()-fc_started}
(L2_OUT/'continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FORMING_LIFT2_CONTINUOUS_DONE',report['status'],len(fc_passed),len(fc_unproved),fc_error,flush=True)
