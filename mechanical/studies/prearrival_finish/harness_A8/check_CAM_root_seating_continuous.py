"""Bound the complete insulated-wire seating motion between finite positions.

Use an independently audited 3 mm/mm displacement bound for every curve span
and nonrotating contact. The four identical upper X(Z) transitions have an
analytic packing bound; all other wire pairs, source solids and contacts
retain spatial discretization and temporal-displacement allowances.
"""
from pathlib import Path
RC_SCRIPT=Path(__file__).resolve();RC_ROOT=RC_SCRIPT.parent
RC_HELPER=RC_ROOT/'refine_CAM_root_seating.py';__file__=str(RC_HELPER)
exec(compile(RC_HELPER.read_text().split('\nrx_rows=[];',1)[0],str(RC_HELPER),'exec'),globals())
__file__=str(RC_SCRIPT)
rc_math_file=RX_OUT/'math_bounds.json';rc_math=json.loads(rc_math_file.read_text())
rc_finite_file=RX_OUT/'screen.json';rc_finite=json.loads(rc_finite_file.read_text())
assert rc_math['status']==rc_finite['status']=='PASS'
assert rc_math['source_finite_sha256']==sha(rc_finite_file)
assert rc_math['script_sha256']==sha(RC_ROOT/'audit_CAM_root_seating_math.py')
rc_start=time.time();rc_passed=[];rc_unproved=[];rc_tests=0
rc_L=rc_math['chosen_global_displacement_lipschitz'];assert rc_L==3.
rc_min_length=math.inf


def rc_sample(p):
    s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    tree=KDTree(len(p))
    for i,pt in enumerate(p):tree.insert(Vector(pt),i)
    tree.balance()
    return p,s,tree,float(np.diff(s).max())


def rc_self(p,error,temporal):
    sample=rc_sample(p);arc=sample[1]
    grid=np.linspace(0,arc[-1],int(math.ceil(arc[-1]/.04))+1)
    coarse=np.column_stack([np.interp(grid,arc,p[:,k]) for k in range(3)])
    # Curvature is bounded for the entire offset interval by math_bounds.
    # Added chord error encloses the smooth curve between coarse points.
    err=error+.0401**2/(8*7.)
    return self_check(rc_sample(coarse),err+temporal)


def rc_test(a,b):
    global rc_min_length
    mid=(a+b)/2;temporal=rc_L*(b-a)/2
    # This also bounds the small variation of local strand arclength for
    # the self/own-prefix adjacency exclusions below 2.1 mm.
    if temporal>.014:return dict(kind='temporal_bound_too_wide',temporal_mm=temporal)
    curves,info=rs_curves(mid)
    rc_min_length=min(rc_min_length,min(r['terminal_straight_remaining_mm'] for r in info))
    errors=[r['curve_error_bound_mm']+r['length_compensation_bound_mm'] for r in info]
    fans=[];free=[];all_samples=[];contacts=[]
    for slot,p in enumerate(curves):
        zroot=info[slot]['root_mm'][2]
        fans.append(rc_sample(p[p[:,2]<=zroot+1e-9]))
        free.append(rc_sample(p[p[:,2]>=zroot-1e-9]))
        all_samples.append(rc_sample(p))
        _,tr=ft_frame(0.,p[-1]);contacts.append(pw_obstacle(f'root_contact_{slot}','moving',ft_box.transform(tr)))
    for slot,p in enumerate(curves):
        lo=p.min(0);hi=p.max(0)
        for target in rs_targets:
            if np.any(lo>target[4]+1.) or np.any(hi<target[3]-1.):continue
            margin=0. if target[0]=='Root_contact_bed_only' else .3
            hit=fc_wire_check(p,errors[slot],np.full(len(p),temporal),target,margin)
            if hit:return dict(kind='wire_structure',slot=slot,detail=hit)
        hit=rc_self(p,errors[slot],temporal)
        if hit['status']!='PASS':return dict(kind='wire_self',slot=slot,detail=hit)
        for other in range(4):
            hit=sc_pair(p,None,errors[slot],np.full(len(p),temporal),body_samples[other+1,0],body_error,other==slot)
            if hit:return dict(kind='wire_body',slot=slot,other=other,detail=hit)
            if other>slot:
                q=fans[slot][0]
                hit=sc_pair(q,None,errors[slot],np.full(len(q),2*temporal),fans[other],errors[other])
                if hit:return dict(kind='fan_fan',slot=slot,other=other,detail=hit)
            # Upper-upper pairs use the exact common X(Z) slope proof.
            # Upper-to-fan pairs keep both moving displacement bounds.
            q=free[slot][0]
            hit=sc_pair(q,None,errors[slot],np.full(len(q),2*temporal),fans[other],errors[other],other==slot)
            if hit:return dict(kind='free_fan',slot=slot,other=other,detail=hit)
        contact=contacts[slot];m=contact[2];bb=np.array(m.bounding_box())
        for name,_,solid,lower,upper,_ in rs_targets:
            needed=.3+temporal+1e-4
            if np.any(bb[:3]>upper+needed) or np.any(bb[3:]<lower-needed):continue
            volume=max(0.,float((m^solid).volume()));gap=float(m.min_gap(solid,needed+.001))
            if volume>1e-7 or gap<needed:return dict(kind='contact_structure',slot=slot,object=name,gap_mm=gap,required_mm=needed,intersection_mm3=volume)
        for other,q0 in enumerate(curves):
            q=q0
            if other==slot:
                boundary=q[-1].copy();boundary[2]-=2.
                q=np.vstack([q[q[:,2]<boundary[2]-1e-10],boundary])
            hit=fc_wire_check(q,errors[other],np.full(len(q),2*temporal),contact,0.)
            if hit:return dict(kind='contact_wire',slot=slot,other=other,detail=hit)
            q=body_samples[other+1,0][0]
            hit=fc_wire_check(q,body_error,np.full(len(q),temporal),contact,0.)
            if hit:return dict(kind='contact_body',slot=slot,other=other,detail=hit)
            if other>slot:
                volume=max(0.,float((m^contacts[other][2]).volume()));needed=2*temporal+1e-4
                gap=float(m.min_gap(contacts[other][2],needed+.001))
                if volume>1e-7 or gap<needed:return dict(kind='contact_contact',slots=[slot,other],gap_mm=gap,required_mm=needed,intersection_mm3=volume)
    return None


def rc_interval(a,b,depth=0):
    global rc_tests
    rc_tests+=1;hit=rc_test(a,b)
    if hit is None:
        rc_passed.append(dict(offset_interval_mm=[a,b],status='PASS',displacement_bound_mm=rc_L*(b-a)/2))
        if len(rc_passed)%16==0:print('ROOT_CONTINUOUS',len(rc_passed),round(b,6),'tests',rc_tests,'seconds',round(time.time()-rc_start,1),flush=True)
        return
    if depth>=15:
        rc_unproved.append(dict(offset_interval_mm=[a,b],failure=hit))
        print('ROOT_UNPROVED',a,b,hit,flush=True);return
    mid=(a+b)/2;rc_interval(a,mid,depth+1);rc_interval(mid,b,depth+1)


rc_interval(0.,1.5)
ordered=sorted(rc_passed,key=lambda r:r['offset_interval_mm'][0])
covered=bool(ordered and ordered[0]['offset_interval_mm'][0]==0. and ordered[-1]['offset_interval_mm'][1]==1.5
    and all(a['offset_interval_mm'][1]==b['offset_interval_mm'][0] for a,b in zip(ordered,ordered[1:])))
status='PASS' if covered and not rc_unproved else 'BLOCKED'
report=dict(status=status,scope='Continuous collision bounds for the prescribed four-wire insulated-root seating, before installing the root tie',
    source_main_sha256=source_hash,script_sha256=sha(RC_SCRIPT),helper_sha256=sha(RC_HELPER),
    source_finite_sha256=sha(rc_finite_file),source_math_sha256=sha(rc_math_file),
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_root_tie_parts=sorted(rs_omitted),
    ordinary_wire_margin_mm=.3,functional_root_bed_margin_mm=0.,bare_contact_margin_mm=0.,wire_OD_mm=OD,
    root_offset_range_mm=[0.,1.5],complete_coverage=covered,passed_intervals=ordered,unproved_intervals=rc_unproved,
    interval_tests=rc_tests,global_displacement_lipschitz=rc_L,free_free_gap_lower_bound_mm=rc_math['free_free_gap_lower_bound_mm'],
    minimum_remaining_terminal_straight_at_midpoints_mm=rc_min_length,
    local_adjacency_scope='Self-check samples exclude at most 2 mm midpoint arclength; own-prefix at most 1.85 mm. With interval width below .00934 mm, spatial cells and arc variation remain below 2.1 mm; whole-family radius bound 7 mm covers the local connected strand.',
    own_crimp_exclusion_mm=2.,own_crimp_boundary_inserted=True,
    bed_split_difference_mm3=rx_diff,main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    initial_terminal_bypass='NOT_TESTED',tie_threading_and_tightening='NOT_TESTED',physical_handling='NOT_TESTED',
    elapsed_s=time.time()-rc_start)
(RX_OUT/'continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ROOT_CONTINUOUS_DONE',status,len(ordered),len(rc_unproved),round(time.time()-rc_start,2),flush=True)
