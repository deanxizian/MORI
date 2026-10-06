"""Bound the complete prescribed ordered upper contact feed.

The guide and its finite-secant orientation are exactly the same functions
used by the selected finite screen. Between guide knots, the unnormalized
secant D(s)=p(s+eps)-p(s-eps) is affine. Its norm and cross products bound
tangent/frame rotation. A contact point's displacement is bounded by rear
translation plus rotation about that rear. The long final vertical stroke
uses an exact box sweep instead. This proves only the stated space
allocations along this local procedure, not real-terminal or full assembly
qualification. Main CAD and hardware files remain read-only.
"""
from pathlib import Path
OFC_SCRIPT=Path(__file__).resolve();OFC_ROOT=OFC_SCRIPT.parent
OFC_HELPER=OFC_ROOT/'plan_CAM_shifted_upper_feed.py';__file__=str(OFC_HELPER)
exec(compile(OFC_HELPER.read_text().split('\nsf_bounds=',1)[0],str(OFC_HELPER),'exec'),globals())
__file__=str(OFC_SCRIPT)
OFC_OUT=RS_OUT/'ordered_feed_continuous';OFC_OUT.mkdir(exist_ok=True)
ofc_started=time.time();ofc_tests=0;ofc_passed=[];ofc_unproved=[];ofc_saved={}
ofc_finite_path=RS_OUT/'shifted_ordered_feed_handle05/screen.json'
ofc_finite=json.loads(ofc_finite_path.read_text())
ofc_selected=next(r for r in ofc_finite['rows'] if r['allocation']=='requested_space_only' and r['status']=='PASS')
assert ofc_finite['script_sha256']==sha(OFC_HELPER)
SF_HANDLE=.5;sf_roll_mode=1;uf_curves,uf_info=ou_make(1.8,.2)
uf_arcs=[np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))] for q in uf_curves]
ofc_dims=np.array(ofc_selected['dimensions_mm']);ofc_box=manifold.Manifold.cube(ofc_dims,center=True)
ofc_radius=float(np.linalg.norm([ofc_dims[0]/2.,ofc_dims[1]/2.,ofc_dims[2]]))
ofc_eps=.002;ofc_round=2e-7
ofc_src_arrays=np.load(ofc_finite_path.parent/'curves.npz')
for slot,q in enumerate(uf_curves):
    assert np.array_equal(q,ofc_src_arrays[f"{ofc_selected['curve_key_prefix']}_slot{slot}"])
ofc_done=[];ofc_static=[];ofc_max_rates=dict(tangent=0.,frame=0.,roll=0.)


def ofc_at(slot,s):
    q=uf_curves[slot];arc=uf_arcs[slot]
    return np.column_stack([np.interp(np.atleast_1d(s),arc,q[:,k]) for k in range(3)])


def ofc_min_norm_on_segment(a,b):
    delta=b-a;d=float(np.dot(delta,delta))
    t=float(np.clip(-np.dot(a,delta)/d,0.,1.)) if d else 0.
    return float(np.linalg.norm(a+t*delta))


def ofc_ramp_rate(zlo,zhi,lo,hi):
    left=max(0.,min(1.,(zlo-lo)/(hi-lo)))
    right=max(0.,min(1.,(zhi-lo)/(hi-lo)))
    if right<=0. or left>=1.:return 0.
    u=float(np.clip(.5,left,right))
    return 6.*u*(1.-u)/(hi-lo)


def ofc_roll_rate(slot,zlo,zhi):
    if slot==0:lo,hi,outlo,outhi=197.,202.,210.,217.
    elif slot==2:lo,hi,outlo,outhi=208.,215.,219.,225.
    else:return 0.
    # z'(s)<=1 because s is guide-polyline arclength. Bound the derivative
    # of ramp_in * (1-ramp_out), including intervals crossing ramp knots.
    return math.pi/2.*(ofc_ramp_rate(zlo,zhi,lo,hi)*(1.-sf_ramp(zlo,outlo,outhi))+
                       sf_ramp(zhi,lo,hi)*ofc_ramp_rate(zlo,zhi,outlo,outhi))


def ofc_motion_bound(slot,a,b):
    arc=uf_arcs[slot];end=float(arc[-1])
    knots=[a,b]
    for shift in [-ofc_eps,ofc_eps]:
        start=np.searchsorted(arc,a-shift,'right');stop=np.searchsorted(arc,b-shift,'left')
        knots.extend((arc[start:stop]+shift).tolist())
    knots.extend(x for x in [ofc_eps,end-ofc_eps] if a<x<b)
    s=np.unique(np.array(knots));D=ofc_at(slot,np.minimum(end,s+ofc_eps))-ofc_at(slot,np.maximum(0.,s-ofc_eps))
    kappa=0.;phi=0.;minimum_projection=1.
    for i,ds in enumerate(np.diff(s)):
        if ds<1e-12:continue
        d0,d1=D[i],D[i+1];rate=(d1-d0)/ds
        norm=ofc_min_norm_on_segment(d0,d1)-1e-10
        yz=ofc_min_norm_on_segment(d0[1:],d1[1:])-1e-10
        if norm<=0. or yz<=0.:return None
        maximum=max(float(np.linalg.norm(d0)),float(np.linalg.norm(d1)))+1e-10
        minimum_projection=min(minimum_projection,yz/maximum)
        cross=float(np.linalg.norm(np.cross(d0,rate)))+1e-12
        kappa=max(kappa,cross/(norm*norm))
        phi=max(phi,(abs(float(d0[1]*rate[2]-d0[2]*rate[1]))+1e-12)/(yz*yz))
    if minimum_projection<2e-8:return None  # avoid the helper's fallback frame
    # The projected-X frame has Euler angular speed sqrt(theta'^2+phi'^2),
    # and |theta'|<=|T'|. Then add the declared roll about T.
    zlo,zhi=ofc_at(slot,[a,b])[:,2];roll=ofc_roll_rate(slot,float(zlo),float(zhi))
    frame=math.hypot(kappa,phi)
    rate=1.+ofc_radius*(frame+roll)
    for key,value in [('tangent',kappa),('frame',frame),('roll',roll)]:
        ofc_max_rates[key]=max(ofc_max_rates[key],value)
    return dict(displacement_mm=rate*(b-a)/2.+ofc_round,tangent_rate=kappa,
                frame_rate=frame,roll_rate=roll,minimum_frame_projection=minimum_projection,
                affine_secant_intervals=len(s)-1)


def ofc_prefix(slot,end):
    q=uf_curves[slot];arc=uf_arcs[slot]
    if end<=0.:return None
    end=min(end,float(arc[-1]));point=ofc_at(slot,[end])[0]
    return np.vstack([q[arc<end-1e-10],point])


def ofc_check_solid(slot,a,b,solid,motion,vertical=False):
    bb=np.array(solid.bounding_box());need=.3+motion
    for name,group,m,lo,hi,_ in uf_targets:
        if np.any(bb[:3]>hi+need+ofc_round) or np.any(bb[3:]<lo-need-ofc_round):continue
        volume=max(0.,float((solid^m).volume()));gap=float(solid.min_gap(m,need+.001))
        if volume>1e-7 or gap<need:
            return dict(kind='terminal_structure',object=name,gap_mm=gap,required_mm=need,intersection_mm3=volume)
    obstacle=pw_obstacle('ordered_continuous_terminal','moving',solid)
    for other in range(4):
        if other==slot:
            # For the long vertical suffix the remaining trailing wire is
            # coaxial and >=2 mm behind the current rear, at every instant.
            cut=(a if vertical else b)-2.;q=ofc_prefix(slot,cut);e=uf_info[slot]['curve_error_bound_mm']
        elif other in ofc_done:q=uf_curves[other];e=uf_info[other]['curve_error_bound_mm']
        else:q=ou_park[other];e=0.
        if q is not None:
            hit=fc_wire_check(q,e,np.full(len(q),motion),obstacle,0.)
            if hit:return dict(kind='terminal_wire',other=other,detail=hit)
        q,s=body_samples[other+1,0][:2]
        if other==slot and b<2.:
            end=s[-1]-(2.-b);boundary=np.array([np.interp(end,s,q[:,k]) for k in range(3)])
            q=np.vstack([q[s<end-1e-10],boundary])
        hit=fc_wire_check(q,body_error,np.full(len(q),motion),obstacle,0.)
        if hit:return dict(kind='terminal_body',other=other,detail=hit)
        if other!=slot:
            rear=uf_curves[other][-1] if other in ofc_done else ou_park[other][-1]
            fixed=ofc_box.translate((rear+[0.,0.,ofc_dims[2]/2.]).tolist())
            fbb=np.array(fixed.bounding_box())
            if np.any(bb[:3]>fbb[3:]+motion+ofc_round) or np.any(bb[3:]<fbb[:3]-motion-ofc_round):continue
            volume=max(0.,float((solid^fixed).volume()))
            gap=float(solid.min_gap(fixed,motion+.001))
            # Zero-volume touching is permitted for these catalogue space
            # allocations. No generic 0.3 mm contact/contact margin claimed.
            if volume>1e-7 or (motion>0. and gap<motion):
                return dict(kind='terminal_terminal',other=other,gap_mm=gap,required_mm=motion,intersection_mm3=volume)
    return None


def ofc_interval(slot,a,b,depth=0):
    global ofc_tests
    ofc_tests+=1;bound=ofc_motion_bound(slot,a,b)
    if bound is None:hit=dict(kind='frame_bound_unresolved')
    else:
        tr,rear=ou_terminal_pose(slot,(a+b)/2.,ofc_dims)
        hit=ofc_check_solid(slot,a,b,ofc_box.transform(tr),bound['displacement_mm'])
    if hit is None:
        ofc_passed.append(dict(slot=slot,arc_interval_mm=[a,b],method='bounded_guide_pose',**bound));return
    if depth>=13:
        ofc_unproved.append(dict(slot=slot,arc_interval_mm=[a,b],failure=hit,bound=bound))
        print('ORDERED_FEED_UNPROVED',slot,a,b,hit,flush=True);return
    mid=(a+b)/2.;ofc_interval(slot,a,mid,depth+1);ofc_interval(slot,mid,b,depth+1)


for slot in ou_order:
    q=uf_curves[slot];arc=uf_arcs[slot]
    static=ou_wire_stage(slot,ofc_done,uf_curves,uf_info)
    assert static['status']=='PASS',static
    for other in range(4):
        if other==slot:continue
        at=uf_curves[other][-1] if other in ofc_done else ou_park[other][-1]
        fixed=ofc_box.translate((at+[0.,0.,ofc_dims[2]/2.]).tolist())
        hit=fc_wire_check(q,uf_info[slot]['curve_error_bound_mm'],np.zeros(len(q)),pw_obstacle('parked_contact','fixed',fixed),0.)
        assert hit is None,hit
    ofc_static.append(dict(slot=slot,completed_slots=ofc_done.copy(),wire_checks=static,wire_parked_contacts='PASS'))
    root=np.array(uf_info[slot]['root_mm']);ids=np.flatnonzero(np.linalg.norm(q-root,axis=1)<1e-9)
    assert len(ids)>0;root_index=int(ids[-1]);suffix=float(arc[root_index]+2.+ofc_eps)
    start=ofc_at(slot,[suffix])[0];end=q[-1]
    assert np.all(q[root_index:,0]==root[0]) and np.all(q[root_index:,1]==root[1])
    assert start[2]>225. and np.linalg.norm(start[:2]-end[:2])<1e-12
    # Both rear position and contact orientation are exactly vertical here.
    lo=start+[-ofc_dims[0]/2.,-ofc_dims[1]/2.,0.]
    hi=end+[ofc_dims[0]/2.,ofc_dims[1]/2.,ofc_dims[2]]
    sweep=box(lo,hi);hit=ofc_check_solid(slot,suffix,float(arc[-1]),sweep,0.,True)
    if hit:ofc_unproved.append(dict(slot=slot,arc_interval_mm=[suffix,float(arc[-1])],failure=hit,method='exact_vertical_sweep'))
    else:ofc_passed.append(dict(slot=slot,arc_interval_mm=[suffix,float(arc[-1])],method='exact_vertical_sweep',own_tail_axial_gap_mm=2.-OD/2.))
    nodes=np.linspace(0.,suffix,int(math.ceil(suffix/.25))+1)
    for i,(a,b) in enumerate(zip(nodes,nodes[1:])):
        ofc_interval(slot,float(a),float(b))
        if (i+1)%40==0:print('ORDERED_FEED_CONTINUOUS',slot,i+1,len(nodes)-1,'passed',len(ofc_passed),'unproved',len(ofc_unproved),'s',round(time.time()-ofc_started,1),flush=True)
    ofc_done.append(slot)
    print('ORDERED_FEED_SLOT_DONE',slot,'s',round(time.time()-ofc_started,1),flush=True)
ofc_coverage=[]
for slot in ou_order:
    rows=sorted([r for r in ofc_passed if r['slot']==slot],key=lambda r:r['arc_interval_mm'][0])
    complete=bool(rows and rows[0]['arc_interval_mm'][0]==0. and rows[-1]['arc_interval_mm'][1]==float(uf_arcs[slot][-1]) and
                  all(a['arc_interval_mm'][1]==b['arc_interval_mm'][0] for a,b in zip(rows,rows[1:])))
    ofc_coverage.append(dict(slot=slot,complete=complete,intervals=len(rows)))
report=dict(status='PASS' if not ofc_unproved and all(r['complete'] for r in ofc_coverage) else 'BLOCKED',
    scope='Continuous contact/geometry bounds for the prescribed ordered upper-feed candidate only',
    source_main_sha256=source_hash,script_sha256=sha(OFC_SCRIPT),helper_sha256=sha(OFC_HELPER),
    source_finite_sha256=sha(ofc_finite_path),source_curves_sha256=sha(ofc_finite_path.parent/'curves.npz'),
    source_curve_key=ofc_selected['curve_key_prefix'],source_fixture_ids=[t[0] for t in uf_targets],
    wire_order=ou_order,wire_OD_mm=OD,terminal_space_allocation_mm=ofc_dims.tolist(),
    terminal_space_evidence='ASSUMED space allocation, not a complete vendor terminal or crimp profile',
    structure_margin_mm=.3,terminal_wire_margin_mm=0.,wire_wire_margin_mm=.3,own_crimp_exclusion_mm=2.,
    secant_half_span_mm=ofc_eps,point_roundoff_allocation_mm=ofc_round,
    displacement_basis='Rear speed <=1; exact affine secant segments bound tangent and projected-X-frame rotation; independent declared roll bound',
    static_wire_checks=ofc_static,coverage=ofc_coverage,passed_intervals=ofc_passed,unproved_intervals=ofc_unproved,
    interval_tests=ofc_tests,observed_maximum_certified_rates=ofc_max_rates,
    body_end_material_supply='NOT_TESTED',recovery_continuous='NOT_TESTED',
    physical_wire_torsion_and_handling='NOT_TESTED',actual_terminal_profile='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-ofc_started)
(OFC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ORDERED_FEED_CONTINUOUS_DONE',report['status'],len(ofc_passed),len(ofc_unproved),round(time.time()-ofc_started,1),flush=True)
