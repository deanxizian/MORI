"""Join the stored 13-mm upright neck exit to each ordered-feed start.

Each pending lead is returned down its existing vertical route before its
curved feed. Check the whole contact sweep with all earlier completed leads
present. This needs loose material below the neck; no body-end supply or
operator access is certified here.
"""
from pathlib import Path
RTR_SCRIPT=Path(__file__).resolve();RTR_ROOT=RTR_SCRIPT.parent
RTR_HELPER=RTR_ROOT/'plan_CAM_shifted_upper_feed.py';__file__=str(RTR_HELPER)
exec(compile(RTR_HELPER.read_text().split('\nsf_bounds=',1)[0],str(RTR_HELPER),'exec'),globals())
__file__=str(RTR_SCRIPT)
RTR_OUT=RS_OUT/'ordered_feed_retraction';RTR_OUT.mkdir(exist_ok=True)
rtr_started=time.time();rtr_rows=[]
rtr_feed=RS_OUT/'shifted_ordered_feed_handle05/screen.json'
rtr_receipt=json.loads(rtr_feed.read_text())
rtr_selected=next(r for r in rtr_receipt['rows'] if r['allocation']=='requested_space_only' and r['status']=='PASS')
SF_HANDLE=.5;sf_roll_mode=1;uf_curves,uf_info=ou_make(1.8,.2)
uf_arcs=[np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))] for q in uf_curves]
rtr_dims=np.array(rtr_selected['dimensions_mm']);rtr_template=manifold.Manifold.cube(rtr_dims,center=True)
rtr_neck_file=RTR_ROOT/'assembly_feed_v3/relaxation_curves.npz';rtr_neck=np.load(rtr_neck_file)
rtr_phases=[225,135,315,45];rtr_done=[]


for slot in ou_order:
    lower=ou_park[slot][0];upper=ou_park[slot][-1];failures=[]
    tr,rear=ou_terminal_pose(slot,0.,rtr_dims)
    # The guide uses a finite secant tangent. Join its tiny initial tilt by
    # a continuous shortest rotation about the rear datum, rather than
    # weakening the endpoint-identity tolerance or declaring it vertical.
    rot=tr[:,:3]
    assert np.linalg.norm(rot.T@rot-np.eye(3))<1e-8
    angle=math.acos(float(np.clip((np.trace(rot)-1.)/2.,-1.,1.)))
    radius=float(np.linalg.norm([rtr_dims[0]/2.,rtr_dims[1]/2.,rtr_dims[2]]))
    rotation_bound=2.*radius*math.sin(angle/2.)+1e-6
    lo=lower+[-rtr_dims[0]/2.,-rtr_dims[1]/2.,0.]-rotation_bound
    hi=upper+[rtr_dims[0]/2.,rtr_dims[1]/2.,rtr_dims[2]]+rotation_bound
    sweep=box(lo,hi);obstacle=pw_obstacle('ordered_retraction_contact_sweep','moving',sweep)
    nearest=.301
    for name,group,m,l,h,_ in uf_targets:
        if np.any(lo>h+.301) or np.any(hi<l-.301):continue
        gap=float(sweep.min_gap(m,.301));volume=max(0.,float((sweep^m).volume()))
        nearest=min(nearest,gap)
        if gap<.3 or volume>1e-7:failures.append(dict(kind='structure',object=name,gap_mm=gap,intersection_mm3=volume))
    active=ou_park[slot];ae=0.;sm=fine(active,.01)
    for target in rs_targets:
        hit=fc_wire_check(active,ae,np.zeros(len(active)),target,.3)
        if hit:failures.append(dict(kind='wire_structure',detail=hit))
    for other in range(4):
        body=body_samples[other+1,0]
        checked=own_prefix_check(sm,body,0.,body_error) if other==slot else pair(sm,body,0.,body_error)
        if checked['status']!='PASS':failures.append(dict(kind='park_wire_body',other=other,detail=checked))
        q,s=body[0],body[1]
        if other==slot:
            end=s[-1]-2.;boundary=np.array([np.interp(end,s,q[:,k]) for k in range(3)])
            q=np.vstack([q[s<end-1e-10],boundary])
        hit=fc_wire_check(q,body_error,np.zeros(len(q)),obstacle,0.)
        if hit:failures.append(dict(kind='terminal_body',other=other,detail=hit))
        if other==slot:continue
        q=uf_curves[other] if other in rtr_done else ou_park[other]
        error=uf_info[other]['curve_error_bound_mm'] if other in rtr_done else 0.
        hit=fc_wire_check(q,error,np.zeros(len(q)),obstacle,0.)
        if hit:failures.append(dict(kind='terminal_other_wire',other=other,detail=hit))
        checked=pair(sm,fine(q,.01),0.,error)
        if checked['status']!='PASS':failures.append(dict(kind='park_wire_other',other=other,detail=checked))
        terminal=rtr_template.translate((q[-1]+[0.,0.,rtr_dims[2]/2.]).tolist())
        volume=max(0.,float((sweep^terminal).volume()))
        if volume>1e-7:failures.append(dict(kind='terminal_terminal',other=other,intersection_mm3=volume))
        hit=fc_wire_check(active,0.,np.zeros(len(active)),pw_obstacle('other_terminal','fixed',terminal),0.)
        if hit:failures.append(dict(kind='park_wire_terminal',other=other,detail=hit))
    expected=np.column_stack([np.eye(3),lower+[0.,0.,rtr_dims[2]/2.]])
    pose_delta=float(np.abs(tr-expected).max())
    neck_end=rtr_neck[f'introduce_slack_10_{rtr_phases[slot]}'][-1]
    neck_delta=float(np.linalg.norm(upper-neck_end))
    if np.linalg.norm(rear-lower)>1e-8 or neck_delta>1e-5:
        failures.append(dict(kind='endpoint_identity',rear_delta=float(np.linalg.norm(rear-lower)),neck_delta=neck_delta))
    rtr_rows.append(dict(slot=slot,completed_slots=rtr_done.copy(),status='PASS' if not failures else 'BLOCKED',
        failures=failures,source_neck_endpoint_difference_mm=neck_delta,
        feed_start_transform_difference=pose_delta,start_rear_mm=upper.tolist(),end_rear_mm=lower.tolist(),
        initial_guide_tilt_deg=math.degrees(angle),rotation_bridge_bound_mm=rotation_bound,
        rotation_bridge='Shortest rotation about fixed rear datum, covered by the expanded swept prism',
        exact_swept_prism_bounds_mm=[lo.tolist(),hi.tolist()],nearest_structure_capped_mm=nearest))
    rtr_done.append(slot)
    print('ORDERED_RETRACTION',slot,rtr_rows[-1]['status'],failures,flush=True)
report=dict(status='PASS' if all(r['status']=='PASS' for r in rtr_rows) else 'BLOCKED',
    scope='Vertical contact sweep plus bounded initial tangent rotation and maximum trailing wire before each curved ordered feed',
    source_main_sha256=source_hash,script_sha256=sha(RTR_SCRIPT),helper_sha256=sha(RTR_HELPER),
    source_feed_sha256=sha(rtr_feed),source_neck_sha256=sha(rtr_neck_file),
    wire_order=ou_order,terminal_space_allocation_mm=rtr_dims.tolist(),wire_OD_mm=OD,
    source_fixture_ids=[t[0] for t in uf_targets],uninstalled_root_tie_parts=sorted(rs_omitted),
    rows=rtr_rows,structure_margin_mm=.3,terminal_wire_margin_mm=0.,wire_wire_margin_mm=.3,
    own_crimp_exclusion_mm=2.,own_trailing_wire_argument='Vertical wire always below moving rear plane; last 2 mm excluded only as explicit crimp region',
    body_end_material_retraction_mm=13.,body_end_material_supply='NOT_TESTED',
    complete_neck_sequence_geometry_identity='NOT_TESTED',actual_terminal_profile='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-rtr_started)
(RTR_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ORDERED_RETRACTION_DONE',report['status'],round(time.time()-rtr_started,1),flush=True)
