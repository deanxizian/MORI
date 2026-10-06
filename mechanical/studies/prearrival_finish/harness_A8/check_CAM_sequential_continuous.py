"""Bound the complete prescribed sequential forming motion between nodes.

At fixed material parameter u, the X quintic is invariant. Planar motion
is bounded by the integral of the tangent-angle derivative; the temporary
height H=h0+A(f)*sin(pi*f) allows piecewise-linear A. Lateral rotation is
bounded by its exact chord displacement about the unchanged vertical root.
All bounds include each sample's material cell, not just the sample centre.
Static conductors stay present. Nominal bare-contact nonpenetration and the
ordinary0.3mm wire/structure margin are different scopes, never conflated.
"""
from pathlib import Path
SC_SCRIPT=Path(__file__).resolve();SC_ROOT=SC_SCRIPT.parent
SC_HELPER=SC_ROOT/'refine_CAM_outer_contact_path.py';__file__=str(SC_HELPER)
exec(compile(SC_HELPER.read_text().split('\ntc_grid=',1)[0],str(SC_HELPER),'exec'),globals())
__file__=str(SC_SCRIPT)
SC_OUT=TC_OUT/'continuous';SC_OUT.mkdir(exist_ok=True)
sc_path=json.loads((TC_OUT/'screen.json').read_text());assert sc_path['status']=='PASS'
sc_start=time.time();sc_tests=0;sc_passed=[];sc_unproved=[];sc_nominal=[];sc_static=[];sc_math=[]
sc_K=1./min(fc_R,fc_r)+(10.*math.sqrt(3.)/3.)*1.8875/16.**2
sc_max_slope=1.8875*1.875/16.;sc_arc_speed=math.sqrt(1.+sc_max_slope**2)
sc_length_bound=fc_end*sc_arc_speed
sc_self_step=.065;sc_self_deficit=sc_length_bound*(sc_self_step*sc_K)**2/8.
sc_local_cutoff=1.85
assert 2.-sc_self_step-2.*sc_self_deficit>sc_local_cutoff
sc_contact_radius=float(np.linalg.norm([ft_dims[0]/2.,ft_dims[1]/2.,ft_dims[2]]))
sc_contact_rx_radius=math.hypot(ft_dims[1]/2.,ft_dims[2])
sc_max_depth=14


def sc_control(edge,f):
    a,b=edge;t=(f-a['fraction'])/(b['fraction']-a['fraction'])
    return (a['amplitude_mm']+t*(b['amplitude_mm']-a['amplitude_mm']),
            a['side_angle_deg']+t*(b['side_angle_deg']-a['side_angle_deg']))


def sc_curve(stage,edge,f):
    global fc_amplitude,st_angle_max
    fc_amplitude,st_angle_max=sc_control(edge,f);p,u,e=fc_curve(f)
    p=p+[xx[da_order[stage]]-xx[0],0.,0.]
    # The own-crimp exclusion boundary lies on the final straight. Insert it
    # exactly instead of accidentally excluding one extra sampling interval.
    v=np.sort(np.unique(np.r_[u,fc_end-2.]))
    q=np.column_stack([np.interp(v,u,p[:,i]) for i in range(3)])
    return q,v,2.*e


def sc_bound(stage,edge,a,b,p,u,cell=True):
    half=(b-a)/2.;f=(a+b)/2.;aa,al=sc_control(edge,a);ab,bl=sc_control(edge,b)
    amin=min(aa,ab);amax=max(aa,ab);ap=abs((edge[1]['amplitude_mm']-edge[0]['amplitude_mm'])/(edge[1]['fraction']-edge[0]['fraction']))
    smax=1. if a<=.5<=b else max(math.sin(math.pi*a),math.sin(math.pi*b))
    hmin=fc_h0+amin*min(math.sin(math.pi*a),math.sin(math.pi*b))
    hp=ap*smax+amax*math.pi*max(abs(math.cos(math.pi*a)),abs(math.cos(math.pi*b)))
    du=float(np.diff(u).max())/2. if cell and len(u)>1 else 0.
    w=np.minimum(u+du,fc_end)
    integ=fc_integrated_ramp(w,hmin,fc_R,math.pi)
    integ+=fc_integrated_ramp(w,fc_B,fc_r,math.pi/2.)+fc_integrated_ramp(w,fc_C,fc_r,math.pi/2.)
    vplan=integ+b*hp/fc_R*np.minimum(np.maximum(w-hmin,0.),math.pi*fc_R)
    pivot=np.array([xx[da_order[stage]],-1.5,230.])
    rho=np.linalg.norm((p-pivot)[:,:2],axis=1)+sc_arc_speed*du
    alpha_half=abs(math.radians(bl-al))/2.
    rotation=2.*math.sin(min(alpha_half,math.pi)/2.)*rho
    displacement=vplan*half+rotation
    # Root cells fully inside the documented unchanged first4.3mm stay put.
    displacement[u+du<=4.3]=0.
    return displacement,{'H_min_mm':hmin,'Hprime_abs_bound_mm':hp,'material_cell_half_mm':du,
        'maximum_point_displacement_mm':float(displacement.max()),'alpha_half_rad':alpha_half}


def sc_contact_bound(stage,edge,a,b,p,u):
    d,meta=sc_bound(stage,edge,a,b,p[-1:],u[-1:],False);half=(b-a)/2.
    alpha=meta['alpha_half_rad']
    return float(d[0]+2.*math.sin(min(alpha,math.pi)/2.)*sc_contact_radius
        +2.*math.sin(min(2.*math.pi*half,math.pi)/2.)*sc_contact_rx_radius)


def sc_pair(p,u,e,d,target,other_error,own=False):
    q,s,tree,step=target;ds=np.linalg.norm(np.diff(p,axis=0),axis=1)
    space=np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2.
    req=OD+.3+space+step/2.+e+other_error+1e-4+d
    lo=q.min(0);hi=q.max(0);lower=np.linalg.norm(np.maximum(np.maximum(lo-p,p-hi),0.),axis=1)
    ids=np.flatnonzero(lower<req)
    arcs=np.r_[0.,np.cumsum(ds)] if own else None
    for i in ids:
        if own:
            hits=[(j,float(dist)) for _,j,dist in tree.find_range(Vector(p[i]),float(req[i]))
                if float(arcs[i]+s[-1]-s[j])>sc_local_cutoff]
            if not hits:continue
            j,dist=min(hits,key=lambda x:x[1])
        else:_,j,dist=tree.find(Vector(p[i]));dist=float(dist)
        if dist<req[i]:return {'point_index':int(i),'target_index':int(j),'point_mm':p[i].tolist(),
            'target_point_mm':q[j].tolist(),'distance_mm':dist,'required_mm':float(req[i]),'temporal_mm':float(d[i])}
    return None


def sc_self(stage,edge,a,b,p,u,e):
    ids=np.unique(np.r_[np.arange(0,len(p),6),len(p)-1]).astype(int);q=p[ids];v=u[ids]
    ds=np.linalg.norm(np.diff(q,axis=0),axis=1);step=float(ds.max());assert step<sc_self_step
    err=e+sc_K*float(np.diff(v).max())**2/8.
    temporal,_=sc_bound(stage,edge,a,b,q,v)
    arcs=np.r_[0.,np.cumsum(ds)];tree=KDTree(len(q))
    for i,x in enumerate(q):tree.insert(Vector(x),i)
    tree.balance();base=OD+.3+step+2.*err+1e-4;maxd=float(temporal.max())
    for i,x in enumerate(q):
        radius=base+float(temporal[i])+maxd
        for _,j,dist in tree.find_range(Vector(x),radius):
            if j<=i or abs(float(arcs[j]-arcs[i]))<=sc_local_cutoff:continue
            required=base+float(temporal[i]+temporal[j])
            if dist<required:return {'sample_indices':[i,int(j)],'distance_mm':float(dist),
                'required_mm':required,'temporal_mm':float(temporal[i]+temporal[j])}
    return None


def sc_test(stage,edge,a,b):
    f=(a+b)/2.;p,u,e=sc_curve(stage,edge,f);d,meta=sc_bound(stage,edge,a,b,p,u)
    cd=sc_contact_bound(stage,edge,a,b,p,u);slot=da_order[stage]
    if max(float(d.max()),cd)>1.5:return {'kind':'bound_too_wide','wire_mm':float(d.max()),'contact_mm':cd}
    _,tr=ft_frame(f,p[-1]);contact=pw_obstacle('moving_bare_contact','moving',ft_box.transform(tr))
    cb=np.array(contact[2].bounding_box())
    for name,group,m,lo,hi,tree in fm_targets:
        needed=.3+cd+1e-4
        if np.any(cb[:3]>hi+needed) or np.any(cb[3:]<lo-needed):continue
        volume=max(0.,float((contact[2]^m).volume()));gap=float(contact[2].min_gap(m,needed+.001))
        if volume>1e-7 or gap<needed:return {'kind':'contact_structure','object':name,'gap_mm':gap,
            'required_mm':needed,'intersection_mm3':volume,'temporal_mm':cd}
    for target in fc_targets:
        name=target[0]
        if name in fc_root_contacts:pieces=[(u>=4.3-1e-9,.3)]
        elif name=='CAM_bed_only':pieces=[(u<=fc_seat_start+1e-9,.3),
            ((u>=fc_seat_start-1e-9)&(u<=fc_seat_end+1e-9),0.),(u>=fc_seat_end-1e-9,.3)]
        else:pieces=[(np.ones(len(u),bool),.3)]
        for mask,margin in pieces:
            hit=fc_wire_check(p[mask],e,d[mask],target,margin)
            if hit:return {'kind':'wire_structure','failure':hit}
    for other in range(4):
        phase=1. if da_order.index(other)<stage else 0.
        hit=sc_pair(p,u,e,d,pw_fans[other],pw_fan_errors[other],other==slot)
        if hit:return {'kind':'wire_yaw_fan','other_slot':other,'failure':hit}
        hit=sc_pair(p,u,e,d,body_samples[other+1,0],body_error)
        if hit:return {'kind':'wire_body_prefix','other_slot':other,'failure':hit}
        if other!=slot:
            q,qu,qe,qsm=oe_static[other,phase]
            hit=sc_pair(p,u,e,d,qsm,qe)
            if hit:return {'kind':'wire_fixed_free','other_slot':other,'failure':hit}
            fixed=tc_static[other,phase]
            hit=fc_wire_check(p,e,d,fixed,0.)
            if hit:return {'kind':'wire_fixed_contact','other_slot':other,'failure':hit}
            volume=max(0.,float((contact[2]^fixed[2]).volume()));needed=cd+1e-4
            gap=float(contact[2].min_gap(fixed[2],needed+.001))
            if volume>1e-7 or gap<needed:return {'kind':'contact_fixed_contact','other_slot':other,
                'gap_mm':gap,'required_mm':needed,'intersection_mm3':volume,'temporal_mm':cd}
            hit=fc_wire_check(q,qe,np.full(len(q),cd),contact,0.)
            if hit:return {'kind':'contact_fixed_free','other_slot':other,'failure':hit}
        for group,sm,err in [('yaw_fan',pw_fans[other],pw_fan_errors[other]),('body',body_samples[other+1,0],body_error)]:
            q=sm[0];hit=fc_wire_check(q,err,np.full(len(q),cd),contact,0.)
            if hit:return {'kind':'contact_'+group,'other_slot':other,'failure':hit}
    keep=u<=fc_end-2.+1e-10
    hit=fc_wire_check(p[keep],e,d[keep]+cd,contact,0.)
    if hit:return {'kind':'contact_own_nonlocal_wire','failure':hit}
    hit=sc_self(stage,edge,a,b,p,u,e)
    if hit:return {'kind':'nonlocal_wire_self','failure':hit}
    return None


def sc_interval(stage,edge,a,b,depth=0):
    global sc_tests
    sc_tests+=1;hit=sc_test(stage,edge,a,b)
    if hit:
        mid=(a+b)/2.
        # A nominal check distinguishes a genuine spatial screening failure
        # from a loose motion bound. Stop at a real unresolved state first.
        if depth>=2:
            nominal=sc_test(stage,edge,mid,mid)
            if nominal is not None:
                row={'stage':stage,'active_slot':da_order[stage],'fraction':mid,'failure':nominal}
                sc_nominal.append(row);sc_unproved.append({'stage':stage,'interval':[a,b],'nominal_failure':row})
                raise RuntimeError('Nominal intermediate position failed; refine the path before full continuous audit')
        if depth>=sc_max_depth:
            sc_unproved.append({'stage':stage,'interval':[a,b],'failure':hit});raise RuntimeError('Displacement bound unresolved at depth limit')
        sc_interval(stage,edge,a,mid,depth+1);sc_interval(stage,edge,mid,b,depth+1)
    else:
        sc_passed.append({'stage':stage,'interval':[a,b],'status':'PASS'})
        if len(sc_passed)%20==0:print('SEQUENTIAL_CONTINUOUS',stage,a,b,'passed',len(sc_passed),'tests',sc_tests,'sec',round(time.time()-sc_start,1),flush=True)


# Static mixed states are checked once; their geometry is invariant during a
# stage. Earlier contact replay covers every pair of these same fixed states.
for stage in range(4):
    slot=da_order[stage];fixed=[]
    for other in range(4):
        if other==slot:continue
        phase=1. if da_order.index(other)<stage else 0.;q,qu,qe,sm=oe_static[other,phase]
        fixed.append((other,phase,sm,qe))
    for a,b in itertools.combinations(fixed,2):
        result=pair(a[2],b[2],a[3],b[3]);sc_static.append({'stage':stage,'slots':[a[0],b[0]],'phases':[a[1],b[1]],**result})
assert all(r['status']=='PASS' for r in sc_static)
oc=json.loads((TC_SOURCE/'contacts.json').read_text())
for stage in range(4):
    r=next(r for r in oc['rows'] if r['stage']==stage and r['fraction']==0.)
    assert r['nominal_nonpenetration']=='PASS'
assert all(r['status']=='PASS' for r in oc['static_wire_fixture_checks'])

# Audit the hardest changed edges first; a known obstruction should not be
# hidden behind hours of checks on distant, easy portions of the route.
edges=[(s['stage'],a,b) for s in sc_path['stages'] for a,b in zip(s['path'],s['path'][1:])]
priority=[(3,.825),(3,.775),(3,.65),(3,0.),(2,.8),(2,0.)]
edges.sort(key=lambda x:(priority.index((x[0],x[1]['fraction'])) if (x[0],x[1]['fraction']) in priority else len(priority),x[0],x[1]['fraction']))
try:
    for stage,a,b in edges:
        print('SEQUENTIAL_EDGE',stage,a['fraction'],b['fraction'],flush=True)
        sc_interval(stage,(a,b),a['fraction'],b['fraction'])
    sc_error=None
except Exception as exc:sc_error=repr(exc)
coverage=[]
for stage in range(4):
    rows=sorted([r for r in sc_passed if r['stage']==stage],key=lambda r:r['interval'][0])
    ok=bool(rows and rows[0]['interval'][0]==0. and rows[-1]['interval'][1]==1.
        and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
    coverage.append({'stage':stage,'complete':ok,'passed_intervals':len(rows)})
good=all(r['complete'] for r in coverage) and not sc_unproved and sc_error is None
report={'status':'PASS' if good else 'BLOCKED','scope':'Continuous bounds for sequential forming wires and nominal bare contacts with static mixed conductors retained',
    'source_main_sha256':source_hash,'script_sha256':sha(SC_SCRIPT),'helper_sha256':sha(SC_HELPER),
    'source_path_sha256':sha(TC_OUT/'screen.json'),'source_static_contact_audit_sha256':sha(TC_SOURCE/'contacts.json'),
    'coverage':coverage,'complete_coverage':good,'passed_intervals':sc_passed,'unproved_intervals':sc_unproved,
    'nominal_intermediate_failures':sc_nominal,'interval_tests':sc_tests,'error':sc_error,'static_wire_pairs':sc_static,
    'bound_argument':'At fixed material u, integrate Theta plus f*abs(Hprime)/R over the translated upper-turn interval. H=h0+A(f)*sin(pi*f), with piecewise-linear A. Add exact2*sin(dalpha/2)*rho for lateral rotation; enlarge rho and integrated speed over each sample material cell. Contact adds endpoint motion and two rigid rotation chord bounds.',
    'wire_parameter_step_mm':fm_step,'wire_OD_mm':OD,'wire_structure_margin_mm':.3,'contact_structure_margin_mm':.3,
    'bare_contact_nonpenetration_margin_mm':0.,'generic_0_3mm_contact_packing':'BLOCKED',
    'self_test_arclength_cutoff_mm':sc_local_cutoff,'self_coarse_step_upper_mm':sc_self_step,
    'self_arclength_deficit_bound_mm':sc_self_deficit,'own_crimp_local_parameter_exclusion_mm':2.,
    'maximum_curve_acceleration_mm_inv':sc_K,'constant_material_length':'ANALYTICAL_X_QUINTIC_AND_UNIT_PLANAR_TANGENT',
    'physical_crimp_and_handling':'NOT_TESTED','terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-sc_start}
(SC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('SEQUENTIAL_CONTINUOUS_DONE',report['status'],len(sc_passed),sc_error,flush=True)
