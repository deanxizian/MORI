"""Screen a guided upper-terminal feed along the unseated four-wire curves.

This investigates the missing upper approach, not the unresolved connection
from the preceding neck-transit pose or the body-end loose lead. Nominal old
boxes and a separate larger requested-space allocation are kept distinct;
neither represents the newly documented but undimensioned locking lance.
"""
from pathlib import Path
UF_SCRIPT=Path(__file__).resolve();UF_ROOT=UF_SCRIPT.parent
UF_HELPER=UF_ROOT/'refine_CAM_root_seating.py';__file__=str(UF_HELPER)
exec(compile(UF_HELPER.read_text().split('\nrx_rows=[];',1)[0],str(UF_HELPER),'exec'),globals())
__file__=str(UF_SCRIPT)
UF_OUT=RS_OUT/'upper_terminal_feed';UF_OUT.mkdir(exist_ok=True)
uf_start=time.time();uf_curves,uf_info=rs_curves(1.5)
uf_arcs=[np.r_[0.,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))] for p in uf_curves]
uf_targets=[t for t in fm_targets if t[0] not in rs_omitted]
uf_wiretargets=[pw_obstacle(f'body_wire_{i}','fixed',solid) for i,solid in []]
uf_rows=[];uf_saved={};uf_step=.15

def uf_pose(slot,arc,roll_deg,dims):
    p=uf_curves[slot];s=uf_arcs[slot]
    def at(a):return np.array([np.interp(a,s,p[:,k]) for k in range(3)])
    rear=at(arc);eps=.002
    tangent=at(min(s[-1],arc+eps))-at(max(0.,arc-eps));tangent/=np.linalg.norm(tangent)
    x=np.array([1.,0.,0.])-tangent*tangent[0];x/=np.linalg.norm(x)
    y=np.cross(tangent,x);a=math.radians(roll_deg)
    rot=np.column_stack([x*math.cos(a)+y*math.sin(a),-x*math.sin(a)+y*math.cos(a),tangent])
    return np.column_stack([rot,rear+tangent*dims[2]/2.]),rear

def uf_check(slot,arc,roll,dims,template):
    tr,rear=uf_pose(slot,arc,roll,dims);solid=template.transform(tr);bb=np.array(solid.bounding_box())
    failures=[];nearest={'gap_mm':.301,'object':None}
    for name,group,m,lo,hi,_ in uf_targets:
        if np.any(bb[:3]>hi+.301) or np.any(bb[3:]<lo-.301):continue
        gap=float(solid.min_gap(m,.301))
        if gap<nearest['gap_mm']:nearest={'gap_mm':gap,'object':name}
        if gap<.3-1e-6:
            failures.append(dict(kind='structure',object=name,gap_mm=gap,
                intersection_mm3=max(0.,float((solid^m).volume()))))
    target=pw_obstacle('moving_terminal','moving',solid)
    for other,q0 in enumerate(uf_curves):
        if other==slot:
            end=max(0.,arc-2.)
            if end<=.01:continue
            s=uf_arcs[other]
            boundary=np.array([np.interp(end,s,q0[:,k]) for k in range(3)])
            q=np.vstack([q0[s<end-1e-9],boundary])
        else:q=q0
        hit=fc_wire_check(q,uf_info[other]['curve_error_bound_mm'],np.zeros(len(q)),target,0.)
        if hit:failures.append(dict(kind='wire',other=other,detail=hit))
    for other in range(4):
        q=body_samples[other+1,0][0]
        hit=fc_wire_check(q,body_error,np.zeros(len(q)),target,0.)
        if hit:failures.append(dict(kind='body_wire',other=other,detail=hit))
    for other in range(4):
        if other==slot:continue
        _,fixed_tr=ft_frame(0.,uf_curves[other][-1]);fixed_contact=ft_box.transform(fixed_tr)
        if np.any(bb[:3]>np.array(fixed_contact.bounding_box())[3:]) or np.any(bb[3:]<np.array(fixed_contact.bounding_box())[:3]):continue
        volume=max(0.,float((solid^fixed_contact).volume()))
        if volume>1e-7:failures.append(dict(kind='other_terminal',other=other,intersection_mm3=volume))
    return failures,nearest,tr,rear

for label,dims in [('old_nominal_box',[.8,1.35,3.9]),('requested_space_only',[1.,1.8,4.1])]:
    template=manifold.Manifold.cube(dims,center=True)
    for slot in range(4):
        count=int(math.ceil(uf_arcs[slot][-1]/uf_step))+1
        stations=np.linspace(0.,uf_arcs[slot][-1],count)
        for roll in [0.,90.]:
            first_by_object={};failure_count=0;nearest={'gap_mm':.301,'object':None};poses=[]
            for arc in stations:
                failures,gap,tr,rear=uf_check(slot,float(arc),roll,dims,template)
                if gap['gap_mm']<nearest['gap_mm']:nearest={**gap,'arc_mm':float(arc),'rear_mm':rear.tolist()}
                if failures:failure_count+=1
                for fail in failures:
                    key=(fail['kind'],fail.get('object'),fail.get('other'))
                    if key not in first_by_object:
                        first_by_object[key]={**fail,'arc_mm':float(arc),'rear_mm':rear.tolist(),'transform_3x4':tr.tolist()}
                if failures and len(poses)<4:poses.append(tr)
            row=dict(allocation=label,dimensions_mm=dims,slot=slot,roll_deg=roll,stations=count,
                status='PASS' if not first_by_object else 'BLOCKED',failed_station_count=failure_count,
                first_failures=list(first_by_object.values()),nearest_structure=nearest,
                terminal_rear_start_mm=uf_curves[slot][0].tolist(),terminal_rear_end_mm=uf_curves[slot][-1].tolist())
            uf_rows.append(row)
            print('UPPER_FEED',label,slot,roll,row['status'],failure_count,[(x['kind'],x.get('object'),x.get('other')) for x in first_by_object.values()],round(time.time()-uf_start,1),flush=True)
            for i,tr in enumerate(poses):uf_saved[f'{label}_{slot}_roll{roll:g}_hit{i}']=tr
np.savez_compressed(UF_OUT/'failure_poses.npz',**uf_saved)
report=dict(status='PASS',scope='Completed finite diagnostic of two explicit guide-feed envelope sizes; not assembly or real-terminal PASS',
    source_main_sha256=source_hash,script_sha256=sha(UF_SCRIPT),helper_sha256=sha(UF_HELPER),
    source_seating_sha256=sha(RX_OUT/'verification.json'),source_extra_terminal_catalogue_sha256=sha(UF_ROOT/'ssh_catalogue_addendum/JST_eLBT.pdf'),
    wire_OD_mm=OD,ordinary_structure_margin_mm=.3,bare_contact_wire_margin_mm=0.,
    rigid_fixture_ids=[t[0] for t in uf_targets],uninstalled_tie_parts=sorted(rs_omitted),
    all_other_upper_wires_retained=True,all_body_prefixes_retained=True,other_terminal_allocation='Old nominal box',
    slot_order_investigated=False,rows=uf_rows,failure_poses_sha256=sha(UF_OUT/'failure_poses.npz'),
    actual_terminal_lance_and_crimp='NOT_TESTED',continuous_motion='NOT_TESTED',
    connection_from_neck_feed_endpoint='NOT_TESTED',complete_body_end_feed='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-uf_start)
(UF_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('UPPER_FEED_DONE',len(uf_rows),round(time.time()-uf_start,1),flush=True)
