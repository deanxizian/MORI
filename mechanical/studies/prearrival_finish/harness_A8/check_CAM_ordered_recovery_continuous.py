"""Check the full recovery family using independently bounded motion.

The free strands share one X(Z) transition, so their mutual separation is
bounded analytically; touching 1-mm-wide terminal allocations have exactly
1-mm X spacing throughout. Other pairs retain spatial and temporal bounds.
"""
from pathlib import Path
ORC_SCRIPT=Path(__file__).resolve();ORC_ROOT=ORC_SCRIPT.parent
ORC_HELPER=ORC_ROOT/'plan_CAM_ordered_feed_recovery.py';__file__=str(ORC_HELPER)
exec(compile(ORC_HELPER.read_text().split('\nfor fraction in np.linspace',1)[0],str(ORC_HELPER),'exec'),globals())
__file__=str(ORC_SCRIPT)
orc_math_file=FRV_OUT/'math_bounds.json';orc_math=json.loads(orc_math_file.read_text())
assert orc_math['status']=='PASS' and orc_math['source_finite_sha256']==sha(FRV_OUT/'screen.json')
assert orc_math['script_sha256']==sha(ORC_ROOT/'audit_CAM_ordered_recovery_math.py')
orc_started=time.time();orc_passed=[];orc_unproved=[];orc_tests=0
orc_Lfan=orc_math['chosen_fan_lipschitz'];orc_Lcore=orc_math['chosen_upper_core_lipschitz'];orc_Lend=orc_math['chosen_contact_lipschitz']
orc_min_straight=math.inf


def orc_sample(p):
    s=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    tree=KDTree(len(p))
    for i,pt in enumerate(p):tree.insert(Vector(pt),i)
    tree.balance();return p,s,tree,float(np.diff(s).max())


def orc_self(p,error,temporal):
    arc=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
    grid=np.linspace(0.,arc[-1],int(math.ceil(arc[-1]/.04))+1)
    q=np.column_stack([np.interp(grid,arc,p[:,k]) for k in range(3)])
    return self_check(orc_sample(q),error+.0401**2/(8.*7.)+temporal)


def orc_test(a,b):
    global orc_min_straight
    half=(b-a)/2.
    # Cumulative arclength variation has a conservative 8 mm/f bound from
    # fan, upper transition and terminal-straight length compensation. The
    # local adjacency exclusion plus 0.0401-mm cells stays below 2.1 mm.
    if 16.*half+.0401>.1:return dict(kind='adjacency_interval_too_wide')
    mid=(a+b)/2.;curves,info=rs_curves(mid)
    orc_min_straight=min(orc_min_straight,min(x['terminal_straight_remaining_mm'] for x in info))
    errors=[];fans=[];free=[];motions=[];contacts=[]
    for slot,p in enumerate(curves):
        inf=info[slot];zroot=inf['root_mm'][2]
        e=inf['curve_error_bound_mm']+(inf['whole_length_bound_mm'][1]-inf['whole_length_bound_mm'][0])
        errors.append(e);fans.append(orc_sample(p[p[:,2]<=zroot+1e-9]));free.append(orc_sample(p[p[:,2]>=zroot-1e-9]))
        speed=np.full(len(p),orc_Lfan);speed[p[:,2]>zroot+1e-9]=orc_Lcore
        speed[p[:,2]>zroot+frv_upper_core_end-1e-9]=orc_Lend
        motions.append(speed*half)
        _,tr=ft_frame(0.,p[-1]);contacts.append(pw_obstacle(f'recovery_contact_{slot}','moving',ft_box.transform(tr)))
    for slot,p in enumerate(curves):
        temporal=motions[slot];lo=p.min(0);hi=p.max(0)
        for target in rs_targets:
            if np.any(lo>target[4]+1.) or np.any(hi<target[3]-1.):continue
            margin=0. if target[0]=='Root_contact_bed_only' else .3
            hit=fc_wire_check(p,errors[slot],temporal,target,margin)
            if hit:return dict(kind='wire_structure',slot=slot,detail=hit)
        hit=orc_self(p,errors[slot],float(temporal.max()))
        if hit['status']!='PASS':return dict(kind='wire_self',slot=slot,detail=hit)
        for other in range(4):
            hit=sc_pair(p,None,errors[slot],temporal,body_samples[other+1,0],body_error,other==slot)
            if hit:return dict(kind='wire_body',slot=slot,other=other,detail=hit)
            if other>slot:
                q=fans[slot][0]
                hit=sc_pair(q,None,errors[slot],np.full(len(q),2.*orc_Lfan*half),fans[other],errors[other])
                if hit:return dict(kind='fan_fan',slot=slot,other=other,detail=hit)
            q=free[slot][0]
            hit=sc_pair(q,None,errors[slot],np.full(len(q),(orc_Lend+orc_Lfan)*half),fans[other],errors[other],other==slot)
            if hit:return dict(kind='free_fan',slot=slot,other=other,detail=hit)
        contact=contacts[slot];m=contact[2];bb=np.array(m.bounding_box());ct=orc_Lend*half
        for name,_,solid,lower,upper,_ in rs_targets:
            need=.3+ct+1e-4
            if np.any(bb[:3]>upper+need) or np.any(bb[3:]<lower-need):continue
            volume=max(0.,float((m^solid).volume()));gap=float(m.min_gap(solid,need+.001))
            if volume>1e-7 or gap<need:return dict(kind='contact_structure',slot=slot,object=name,gap_mm=gap,required_mm=need,intersection_mm3=volume)
        for other,q0 in enumerate(curves):
            q=q0
            if other==slot:
                boundary=q[-1].copy();boundary[2]-=2.
                q=np.vstack([q[q[:,2]<boundary[2]-1e-10],boundary])
            hit=fc_wire_check(q,errors[other],np.full(len(q),2.*orc_Lend*half),contact,0.)
            if hit:return dict(kind='contact_wire',slot=slot,other=other,detail=hit)
            q=body_samples[other+1,0][0]
            hit=fc_wire_check(q,body_error,np.full(len(q),ct),contact,0.)
            if hit:return dict(kind='contact_body',slot=slot,other=other,detail=hit)
            if other>slot:
                # Whole-family proof in math_bounds: common X shift,
                # identical upright orientation, exactly 1-mm X spacing.
                assert abs((curves[other][-1,0]-p[-1,0])-(other-slot))<1e-9
                if float((m^contacts[other][2]).volume())>1e-7:return dict(kind='contact_contact_numeric_intersection',slots=[slot,other])
    return None


def orc_interval(a,b,depth=0):
    global orc_tests
    orc_tests+=1;hit=orc_test(a,b)
    if hit is None:
        orc_passed.append(dict(fraction_interval=[a,b],fan_motion_bound_mm=orc_Lfan*(b-a)/2.,contact_motion_bound_mm=orc_Lend*(b-a)/2.))
        if len(orc_passed)%16==0:print('ORDERED_RECOVERY_CONTINUOUS',len(orc_passed),round(b,6),'tests',orc_tests,'s',round(time.time()-orc_started,1),flush=True)
        return
    if depth>=15:
        orc_unproved.append(dict(fraction_interval=[a,b],failure=hit));print('ORDERED_RECOVERY_UNPROVED',a,b,hit,flush=True);return
    mid=(a+b)/2.;orc_interval(a,mid,depth+1);orc_interval(mid,b,depth+1)


orc_interval(0.,1.)
ordered=sorted(orc_passed,key=lambda r:r['fraction_interval'][0])
covered=bool(ordered and ordered[0]['fraction_interval'][0]==0. and ordered[-1]['fraction_interval'][1]==1. and all(p['fraction_interval'][1]==q['fraction_interval'][0] for p,q in zip(ordered,ordered[1:])))
report=dict(status='PASS' if covered and not orc_unproved else 'BLOCKED',
    scope='Continuous geometry bounds for the entire declared ordered-feed recovery family',
    source_main_sha256=source_hash,script_sha256=sha(ORC_SCRIPT),helper_sha256=sha(ORC_HELPER),
    source_math_sha256=sha(orc_math_file),source_finite_sha256=sha(FRV_OUT/'screen.json'),
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_root_tie_parts=sorted(rs_omitted),
    terminal_space_allocation_mm=ft_dims.tolist(),terminal_space_evidence='ASSUMED requested space, not a complete vendor profile',
    wire_OD_mm=OD,ordinary_wire_margin_mm=.3,root_contact_bed_margin_mm=0.,terminal_wire_margin_mm=0.,
    complete_coverage=covered,passed_intervals=ordered,unproved_intervals=orc_unproved,interval_tests=orc_tests,
    displacement_lipschitz=dict(fan=orc_Lfan,upper_core=orc_Lcore,terminal=orc_Lend),
    free_free_gap_lower_bound_mm=orc_math['free_free_gap_lower_bound_mm'],
    contact_contact_scope=orc_math['contact_contact_basis'],minimum_terminal_straight_sampled_mm=orc_min_straight,
    local_adjacency_scope='2 mm exclusion with bounded arclength variation plus spatial cells below 2.1 mm; whole-family radius >=7 mm',
    actual_terminal_profile='NOT_TESTED',body_end_material_supply='NOT_TESTED',
    larger_terminal_downstream_seating_and_forming='NOT_TESTED',physical_handling='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-orc_started)
(FRV_OUT/'continuous.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ORDERED_RECOVERY_CONTINUOUS_DONE',report['status'],len(ordered),len(orc_unproved),round(time.time()-orc_started,1),flush=True)
