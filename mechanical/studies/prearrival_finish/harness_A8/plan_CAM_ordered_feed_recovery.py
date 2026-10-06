"""Connect ordered terminal feeding to the existing root-seating start.

The selected larger-space feed has a temporary +0.2 mm X / +1.8 mm Y
fan displacement and a +0.5 mm incoming handle on slot 3. Recover these
while introducing the common, high X transition. Material-length changes
are absorbed in the free terminal straight. No source solid is changed.
This script checks finite positions; it does not certify continuous motion.
"""
from pathlib import Path
FRV_SCRIPT=Path(__file__).resolve();FRV_ROOT=FRV_SCRIPT.parent
FRV_HELPER=FRV_ROOT/'plan_CAM_shifted_upper_feed.py';__file__=str(FRV_HELPER)
exec(compile(FRV_HELPER.read_text().split('\nsf_bounds=',1)[0],str(FRV_HELPER),'exec'),globals())
__file__=str(FRV_SCRIPT)
FRV_OUT=RS_OUT/'ordered_feed_recovery';FRV_OUT.mkdir(exist_ok=True)
frv_started=time.time();frv_rows=[];frv_saved={}
frv_source=RS_OUT/'shifted_ordered_feed_handle05/screen.json'
frv_receipt=json.loads(frv_source.read_text())
frv_selected=next(r for r in frv_receipt['rows'] if r['allocation']=='requested_space_only' and r['status']=='PASS')
assert frv_selected['root_offset_y_mm']==1.8 and frv_selected['common_temporary_dx_mm']==.2
assert frv_receipt['slot3_incoming_handle_extension_mm']==.5
assert frv_receipt['script_sha256']==sha(FRV_HELPER)
frv_start_data=np.load(frv_source.parent/'curves.npz')
frv_end_curves,frv_end_info=rs_curves(1.5)
frv_original_rs_curves=rs_curves
frv_target_lengths=[float(r['allocation_mm']) for r in frv_selected['curves']]
frv_transition_end=float(fm_core_length+fm_tail_parameter)
frv_transition_start=frv_transition_end-16.
frv_upper_core_end=float(fc_end-7.)
assert 0.<frv_transition_start<frv_transition_end<=frv_upper_core_end+1e-8
frv_original_terminal_dims=ft_dims.copy()
ft_dims=np.array(frv_selected['dimensions_mm']);ft_box=manifold.Manifold.cube(ft_dims,center=True)


def frv_upper(fraction,root):
    """Quintic X transition above the robot, on a vertical Z parameter.

    Speed is sqrt(1+x'(u)^2). The exact polynomial second derivative bounds
    both the curve-to-polyline distance and quadrature error. The arclength
    sandwich uses chord sums as a lower bound and |p''| h^2/4 per segment
    as an upper remainder, independent of the 96-point Gauss estimate.
    """
    amp=1.8875*fraction
    knots=[0.,frv_transition_start,frv_transition_end,frv_upper_core_end]
    knots=sorted(set(knots))
    u=np.r_[np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/.008))+1)[:-1]
                           for a,b in zip(knots,knots[1:])]),knots[-1]]
    w=np.clip((frv_transition_end-u)/16.,0.,1.)
    q=root+np.column_stack([-amp*(1.-(10*w**3-15*w**4+6*w**5)),np.zeros(len(u)),u])
    v=(rs_gy+1.)/2.
    derivative=amp/16.*30*v*v*(1.-v)**2
    curved_length=16.*float(np.dot(rs_gw/2.,np.sqrt(1.+derivative*derivative)))
    length=frv_upper_core_end-16.+curved_length
    acceleration=amp*(10*math.sqrt(3)/3.)/16.**2
    error=acceleration*.008**2/8.+1e-12
    # A finer independent chord bound makes the length uncertainty explicit.
    grid=np.linspace(0.,1.,16385)
    x=-amp*(10*grid**3-15*grid**4+6*grid**5)
    chord=float(np.linalg.norm(np.column_stack([np.diff(x),16.*np.diff(grid)]),axis=1).sum())
    rem=acceleration*16.**2/(4.*(len(grid)-1))
    lower=frv_upper_core_end-16.+chord-1e-9
    upper=frv_upper_core_end-16.+chord+rem+1e-9
    assert lower<=length<=upper
    radius=1./acceleration if acceleration else 1e30
    return q,length,error,dict(length_lower_mm=lower,length_upper_mm=upper,
                              minimum_radius_lower_mm=radius,analytic_acceleration_bound=acceleration)


def rs_curves(fraction):
    global SF_HANDLE
    fraction=float(fraction);assert 0.<=fraction<=1.
    offset=1.8-.3*fraction;dx=.2*(1.-fraction);SF_HANDLE=.5*(1.-fraction)
    curves=[];info=[]
    for slot in range(4):
        fan,length,error,bound=ou_fan(slot,offset,dx)
        upper,ul,ue,ub=frv_upper(fraction,fan[-1])
        remaining=frv_target_lengths[slot]-length-ul
        assert remaining>2.
        end=upper[-1]+np.array([0.,0.,remaining])
        straight=np.linspace(upper[-1],end,max(2,math.ceil(remaining/.008)+1))
        q=np.vstack([fan[:-1],upper[:-1],straight])
        whole_low=bound['length_lower_mm']+ub['length_lower_mm']+remaining
        whole_high=bound['length_upper_mm']+ub['length_upper_mm']+remaining
        assert whole_low<=frv_target_lengths[slot]<=whole_high
        bound.update(slot=slot,fraction=fraction,fan_length_mm=length,
                     upper_core_length_mm=ul,upper_radius_lower_mm=ub['minimum_radius_lower_mm'],
                     upper_length_bound_mm=[ub['length_lower_mm'],ub['length_upper_mm']],
                     whole_length_bound_mm=[whole_low,whole_high],
                     source_material_allocation_mm=frv_target_lengths[slot],
                     source_allocation_is_polyline=True,terminal_straight_remaining_mm=remaining,
                     root_mm=fan[-1].tolist(),free_end_mm=end.tolist(),
                     curve_error_bound_mm=max(error,ue),
                     minimum_radius_lower_mm=min(bound['minimum_radius_lower_mm'],ub['minimum_radius_lower_mm']))
        assert bound['minimum_radius_lower_mm']>=7. or bound['radius_status']!='PASS'
        curves.append(q);info.append(bound)
    return curves,info


def frv_compare(q,p):
    # Both reference curves are Z-monotone. Evaluate on the union of their
    # vertex Z values and include endpoint displacement; curvature error is
    # recorded separately instead of pretending equal vertex counts.
    assert min(np.diff(q[:,2]).min(),np.diff(p[:,2]).min())>=-1e-8
    z=np.unique(np.r_[q[:,2],p[:,2]])
    qa=np.column_stack([np.interp(z,q[:,2],q[:,k]) for k in range(3)])
    pa=np.column_stack([np.interp(z,p[:,2],p[:,k]) for k in range(3)])
    return float(np.linalg.norm(qa-pa,axis=1).max())


for fraction in np.linspace(0.,1.,41):
    fraction=float(fraction);outcome,curves,info=rs_check(fraction)
    crimp=rx_exact_crimp(curves,info)
    if outcome['status']=='PASS' and crimp['status']!='PASS':outcome=crimp
    row=dict(fraction=fraction,result=outcome,curves=info,exact_crimp_check=crimp)
    if fraction in [0.,.25,.5,.75,1.]:
        for slot,q in enumerate(curves):frv_saved[f'f{fraction:g}_slot{slot}']=q
    if fraction in [0.,1.]:
        references=[frv_start_data[f"{frv_selected['curve_key_prefix']}_slot{slot}"] for slot in range(4)] if fraction==0. else frv_end_curves
        row['boundary_comparison_mm']=[frv_compare(q,p) for q,p in zip(curves,references)]
    frv_rows.append(row)
    print('FEED_RECOVERY_POSITION',fraction,outcome['status'],outcome.get('kind'),
          outcome.get('slot'),outcome.get('detail'),round(time.time()-frv_started,1),flush=True)
np.savez_compressed(FRV_OUT/'curves.npz',**frv_saved)
frv_boundary=max(max(r.get('boundary_comparison_mm',[0.])) for r in frv_rows)
frv_ok=all(r['result']['status']=='PASS' for r in frv_rows) and frv_boundary<.0001
report=dict(status='PASS' if frv_ok else 'BLOCKED',
    scope='41 finite positions joining selected ordered feed to the existing root-seating start',
    source_main_sha256=source_hash,script_sha256=sha(FRV_SCRIPT),helper_sha256=sha(FRV_HELPER),
    source_feed_sha256=sha(frv_source),source_feed_curve_key=frv_selected['curve_key_prefix'],
    source_root_seating_sha256=sha(RX_OUT/'verification.json'),
    terminal_space_allocation_mm=ft_dims.tolist(),terminal_evidence='ASSUMED space request, not maximum vendor geometry',
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_root_tie_parts=sorted(rs_omitted),
    rows=frv_rows,boundary_match_tolerance_mm=.0001,maximum_boundary_difference_mm=frv_boundary,
    boundary_match='PASS' if frv_boundary<.0001 else 'BLOCKED',
    material_length_method='Bounded circular/Bezier fan plus quintic upper length, compensated only in free terminal straight',
    minimum_terminal_straight_mm=min(c['terminal_straight_remaining_mm'] for r in frv_rows for c in r['curves']),
    minimum_radius_lower_mm=min(c['minimum_radius_lower_mm'] for r in frv_rows for c in r['curves']),
    continuous_motion='NOT_TESTED',body_end_material_supply='NOT_TESTED',
    physical_wire_torsion_and_springback='NOT_TESTED',actual_terminal_profile='NOT_TESTED',
    source_target_uses_smaller_terminal_box=True,target_handoff_of_larger_box='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    curves_sha256=sha(FRV_OUT/'curves.npz'),elapsed_s=time.time()-frv_started)
(FRV_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FEED_RECOVERY_DONE',report['status'],frv_boundary,round(time.time()-frv_started,1),flush=True)
