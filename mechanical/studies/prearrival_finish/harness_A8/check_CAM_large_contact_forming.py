"""Certify larger contact allocations along all four forming stages.

Recheck every moving contact interaction. Reuse the earlier continuous wire
certificate only on exactly unchanged piecewise-linear controls; on changed
edges, repeat wire-to-solid, wire-to-wire and nonlocal self checks. No real
terminal or complete physical installation is certified by these allocations.
"""
from pathlib import Path
LF_SCRIPT=Path(__file__).resolve();LF_ROOT=LF_SCRIPT.parent
LF_HELPER=LF_ROOT/'plan_CAM_large_contact_turn.py';__file__=str(LF_HELPER)
exec(compile(LF_HELPER.read_text().split('\nlt_grid=',1)[0],str(LF_HELPER),'exec'),globals())
__file__=str(LF_SCRIPT)
LF_OUT=LC_OUT/'side_turn';lf_candidate_path=LF_OUT/'screen.json'
lf_candidate=json.loads(lf_candidate_path.read_text())
assert lf_candidate['status']=='PASS' and lf_candidate['source_main_sha256']==source_hash
assert lf_candidate['script_sha256']==sha(LF_HELPER)
assert lf_candidate['source_forming_sha256']==sha(lc_forming_path)
assert lc_forming['complete_four_wire_forming_coverage'] and lc_forming['stage_boundary_identity']=='PASS'
for relative,digest in lc_forming['source_files'].items():assert sha(source.parents[1]/relative)==digest
lf_paths=[s['path'] for s in lc_forming['stages'][:3]]+[lf_candidate['selected']['path']]
sc_contact_radius=float(np.linalg.norm([ft_dims[0]/2.,ft_dims[1]/2.,ft_dims[2]]))
sc_contact_rx_radius=math.hypot(ft_dims[1]/2.,ft_dims[2])
lf_started=time.time();lf_pass=[];lf_unproved=[];lf_tests=0;lf_endpoints=[]


def lf_unchanged(stage,edge):
    if stage<3:return True
    # Candidate includes every original knot: equality at both ends of one
    # edge proves equality throughout that affine control segment.
    for node in edge:
        before=lr_original(node['fraction'])
        if max(abs(before[0]-node['amplitude_mm']),abs(before[1]-node['side_angle_deg']))>1e-12:return False
    return True


def lf_wire_test(stage,edge,a,b,p,u,e,d):
    """Repeat ordinary wire proofs only where the wire motion changed."""
    slot=da_order[stage]
    for target in fc_targets:
        name=target[0]
        if name in fc_root_contacts:pieces=[(u>=4.3-1e-9,.3)]
        elif name=='CAM_bed_only':pieces=[(u<=fc_seat_start+1e-9,.3),
            ((u>=fc_seat_start-1e-9)&(u<=fc_seat_end-1e-9),0.),(u>=fc_seat_end-1e-9,.3)]
        else:pieces=[(np.ones(len(u),bool),.3)]
        for mask,margin in pieces:
            # Preserve the original exact inclusive bed boundary.
            if name=='CAM_bed_only' and margin==0.:mask=(u>=fc_seat_start-1e-9)&(u<=fc_seat_end+1e-9)
            hit=fc_wire_check(p[mask],e,d[mask],target,margin)
            if hit:return dict(kind='wire_structure',failure=hit)
    for other in range(4):
        phase=1. if da_order.index(other)<stage else 0.
        hit=sc_pair(p,u,e,d,pw_fans[other],pw_fan_errors[other],other==slot)
        if hit:return dict(kind='wire_fan',other_slot=other,failure=hit)
        hit=sc_pair(p,u,e,d,body_samples[other+1,0],body_error)
        if hit:return dict(kind='wire_body',other_slot=other,failure=hit)
        if other!=slot:
            q,qu,qe,sm=oe_static[other,phase]
            hit=sc_pair(p,u,e,d,sm,qe)
            if hit:return dict(kind='wire_fixed_free',other_slot=other,failure=hit)
    hit=sc_self(stage,edge,a,b,p,u,e)
    if hit:return dict(kind='wire_nonlocal_self',failure=hit)
    return None


def lf_test(stage,edge,a,b):
    f=(a+b)/2.;slot=da_order[stage]
    p,u,e=sc_curve(stage,edge,f);d,_=sc_bound(stage,edge,a,b,p,u)
    cd=sc_contact_bound(stage,edge,a,b,p,u)
    if max(float(d.max()),cd)>1.5:return dict(kind='bound_too_wide',wire_mm=float(d.max()),contact_mm=cd)
    _,transform=ft_frame(f,p[-1]);contact=pw_obstacle('larger_moving_contact','moving',ft_box.transform(transform))
    shape=contact[2];bounds=np.array(shape.bounding_box());needed=.3+cd+1e-4
    for name,_,solid,lower,upper,_ in fm_targets:
        if np.any(bounds[:3]>upper+needed) or np.any(bounds[3:]<lower-needed):continue
        volume=max(0.,float((shape^solid).volume()));gap=float(shape.min_gap(solid,needed+.001))
        if volume>1e-7 or gap<needed:
            return dict(kind='contact_structure',object=name,gap_mm=gap,required_mm=needed,intersection_mm3=volume)
    angles=[sc_control(edge,t)[1] for t in (a,b)]
    fixed_X_slab=max(abs(v) for v in angles)<1e-12
    for other in range(4):
        phase=1. if da_order.index(other)<stage else 0.
        if other!=slot:
            q,qu,qe,_=oe_static[other,phase];fixed=lc_static[other,phase]
            hit=fc_wire_check(p,e,d,fixed,0.)
            if hit:return dict(kind='wire_fixed_contact',other_slot=other,failure=hit)
            hit=fc_wire_check(q,qe,np.full(len(q),cd),contact,0.)
            if hit:return dict(kind='contact_fixed_wire',other_slot=other,failure=hit)
            volume=max(0.,float((shape^fixed[2]).volume()))
            if fixed_X_slab:
                # No side rotation anywhere in this affine interval. The
                # material X(u) function is fixed; rotation about X cannot
                # enlarge its contact X width. Slab contact is zero volume.
                active_x=float(oe_static[slot,0.][0][-1,0]);other_x=float(q[-1,0])
                assert abs(p[-1,0]-active_x)<1e-9
                assert abs(active_x-other_x)>=ft_dims[0]-1e-10
                if volume>1e-7:return dict(kind='contact_contact_slab_regression',other_slot=other,intersection_mm3=volume)
            else:
                needed=cd+1e-4;gap=float(shape.min_gap(fixed[2],needed+.001))
                if volume>1e-7 or gap<needed:
                    return dict(kind='contact_fixed_contact',other_slot=other,gap_mm=gap,required_mm=needed,intersection_mm3=volume)
        for group,sample,error in [('fan',pw_fans[other],pw_fan_errors[other]),('body',body_samples[other+1,0],body_error)]:
            q=sample[0];hit=fc_wire_check(q,error,np.full(len(q),cd),contact,0.)
            if hit:return dict(kind='contact_'+group,other_slot=other,failure=hit)
    keep=u<=fc_end-2.+1e-10
    hit=fc_wire_check(p[keep],e,d[keep]+cd,contact,0.)
    if hit:return dict(kind='contact_own_nonlocal_wire',failure=hit)
    if not lf_unchanged(stage,edge):return lf_wire_test(stage,edge,a,b,p,u,e,d)
    return None


def lf_interval(stage,edge,a,b,depth=0):
    global lf_tests
    lf_tests+=1;failure=lf_test(stage,edge,a,b)
    if failure is None:
        lf_pass.append(dict(stage=stage,interval=[a,b],status='PASS',unchanged_wire_certificate_reused=lf_unchanged(stage,edge)))
        if len(lf_pass)%100==0:print('LARGER_FORMING_CONT',len(lf_pass),stage,round(b,7),round(time.time()-lf_started,1),flush=True)
        return
    mid=(a+b)/2.
    if depth>=2:
        nominal=lf_test(stage,edge,mid,mid)
        if nominal is not None:
            lf_unproved.append(dict(stage=stage,interval=[a,b],fraction=mid,nominal_failure=nominal))
            raise RuntimeError('Nominal larger-contact screen failure')
    if depth>=16:
        lf_unproved.append(dict(stage=stage,interval=[a,b],failure=failure))
        raise RuntimeError('Larger-contact displacement bound unresolved')
    lf_interval(stage,edge,a,mid,depth+1);lf_interval(stage,edge,mid,b,depth+1)


# Finite static/end-state replay includes every static contact versus all
# source solids, retained conductors and other contacts. Endpoints of the
# changed path are the same as the proven wire sequence.
for stage,path in enumerate(lf_paths):
    for edge,f in [((path[0],path[1]),0.),((path[-2],path[-1]),1.)]:
        failure,curves,contacts=lc_forming_pose(stage,edge,f)
        assert failure is None,failure
        slot=da_order[stage];q,u,e=sc_curve(stage,edge,f);old,old_u,_,_=oe_static[slot,f]
        ref=np.column_stack([np.interp(u,old_u,old[:,k]) for k in range(3)])
        difference=float(np.linalg.norm(q-ref,axis=1).max());assert difference<1e-8
        lf_endpoints.append(dict(stage=stage,fraction=f,status='PASS',maximum_wire_difference_mm=difference))

lf_edges=[(s,a,b) for s,path in enumerate(lf_paths) for a,b in zip(path,path[1:])]
lf_edges.sort(key=lambda row:(not(row[0]==3 and not lf_unchanged(row[0],row[1:])),row[0],row[1]['fraction']))
try:
    for stage,a,b in lf_edges:lf_interval(stage,(a,b),a['fraction'],b['fraction'])
    error=None
except Exception as exc:error=repr(exc)
coverage=[]
for stage in range(4):
    rows=sorted([r for r in lf_pass if r['stage']==stage],key=lambda r:r['interval'][0])
    complete=bool(rows and rows[0]['interval'][0]==0. and rows[-1]['interval'][1]==1.
        and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
    coverage.append(dict(stage=stage,complete=complete,intervals=len(rows)))
status='PASS' if all(r['complete'] for r in coverage) and not lf_unproved and error is None else 'BLOCKED'
report=dict(status=status,scope='Continuous allocated-contact checks for all four forming stages, with unchanged wire proof reused only on identical controls and changed wire edges rechecked',
    script_sha256=sha(LF_SCRIPT),helper_sha256=sha(LF_HELPER),source_main_sha256=source_hash,
    source_candidate_sha256=sha(lf_candidate_path),source_original_forming_sha256=sha(lc_forming_path),
    continuous_helper_sha256=sha(LF_ROOT/'check_CAM_sequential_continuous.py'),
    contact_dimensions_mm=ft_dims.tolist(),contact_evidence='ASSUMED requested space, not vendor or physical qualification',
    coverage=coverage,complete_coverage=status=='PASS',passed_intervals=lf_pass,unproved_intervals=lf_unproved,
    error=error,interval_tests=lf_tests,boundary_rows=lf_endpoints,
    wire_edge_reuse_basis='Identical affine controls on source knots; same helper, source geometry and material X(u); all changed controls rechecked',
    contact_contact_boundary_basis='When side angle is identically zero, fixed separated X slabs prove nonpenetration despite zero clearance; otherwise displacement-expanded distance is checked',
    contact_structure_margin_mm=.3,ordinary_wire_margin_mm=.3,contact_wire_margin_mm=0.,
    own_crimp_exclusion_mm=2.,material_length_invariant=lc_forming['material_length_invariant'],
    radius_lower_bound_mm=lc_forming['nominal_curve_radius_lower_bound_mm'],
    actual_terminal_fit='NOT_TESTED',body_material_supply='NOT_TESTED',tie_threading_and_tightening='NOT_TESTED',
    whole_harness='BLOCKED',main_applied=False,manufacturing_release=False,elapsed_s=time.time()-lf_started)
(LF_OUT/'continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LARGER_FORMING_CONT_DONE',status,len(lf_pass),error,round(time.time()-lf_started,1),flush=True)
