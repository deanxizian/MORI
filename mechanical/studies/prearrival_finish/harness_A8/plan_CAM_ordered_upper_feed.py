"""Screen ordered feeding, with not-yet-fed leads parked at the neck exit.

The old guide test retained every other complete upper wire and forced the
terminal through an already formed high X transition. Here the order is
explicit, the high transition is deferred, and the leftmost wire may use a
temporary wider route beside the pitch servo. No source rigid body changes.
This is a finite geometric screen. Body-end material supply, connection from
the earlier neck procedure, return to the final curves and real terminal
geometry remain separate requirements.
"""
from pathlib import Path
OU_SCRIPT=Path(__file__).resolve();OU_ROOT=OU_SCRIPT.parent
OU_HELPER=OU_ROOT/'screen_CAM_upper_terminal_feed.py';__file__=str(OU_HELPER)
exec(compile(OU_HELPER.read_text().split('\nfor label,dims in ',1)[0],str(OU_HELPER),'exec'),globals())
__file__=str(OU_SCRIPT)
import copy
OU_OUT=RS_OUT/'ordered_upper_feed';OU_OUT.mkdir(exist_ok=True)
ou_started=time.time();ou_saved={};ou_rows=[]
ou_order=[3,2,1,0];ou_step=.15
ou_original_candidates=copy.deepcopy(rs_candidates)
ou_target_arcs=[s.copy() for s in uf_arcs]
ou_target_curves=[q.copy() for q in uf_curves]
ou_target_info=copy.deepcopy(uf_info)
ou_park=[np.linspace(q[0],q[0]+[0.,0.,13.],1626) for q in ou_target_curves]


def ou_fan(slot,offset,slot0_dx):
    if slot!=0:return rs_fan(slot,offset)
    c=ou_original_candidates[0];p=c['parameters']
    point=np.array(c['start_mm']);end=np.array(c['end_mm'])+np.array([slot0_dx,offset,rs_height(offset)])
    deltas=[point[0]-p['side_x_mm'],p['side_y_mm']-point[1],end[0]-p['side_x_mm'],end[1]-p['side_y_mm']]
    axes=[[-1,0,0],[0,1,0],[1,0,0],[0,1,0]];pieces=[];length=0.;errors=[]
    for axis,delta,radius in zip(axes,deltas,p['radii_mm']):
        q,L,e=rs_sbend(point,np.array(axis),delta,radius)
        pieces.append(q);point=q[-1];length+=L;errors.append(e)
    dz=float(end[2]-point[2]);assert dz>0.
    pieces.append(np.linspace(point,end,max(2,int(math.ceil(dz/rs_step))+1)));length+=dz
    q=np.vstack([p[:-1] for p in pieces[:-1]]+[pieces[-1]])
    assert np.linalg.norm(q[0]-ou_target_curves[0][0])<1e-8
    assert np.linalg.norm(q[-1]-end)<1e-8
    return q,length,max(errors),dict(length_lower_mm=length-1e-8,length_upper_mm=length+1e-8,
        minimum_radius_lower_mm=min(p['radii_mm']),radius_status='PASS',unresolved_radius_or_length_intervals=0)


def ou_make(offset,slot0_dx):
    curves=[];infos=[]
    for slot in range(4):
            fan,length,error,bound=ou_fan(slot,offset,slot0_dx)
            # Reuse the existing planned material allocation, not a new cut
            # length. The exact fan length determines the remaining straight.
            total=float(ou_target_arcs[slot][-1]);remaining=total-length
            assert remaining>10.
            tail=np.linspace(fan[-1],fan[-1]+[0.,0.,remaining],
                             int(math.ceil(remaining/.008))+1)
            q=np.vstack([fan[:-1],tail])
            curves.append(q)
            infos.append(dict(slot=slot,**bound,curve_error_bound_mm=error,
                fan_length_mm=length,upper_straight_mm=remaining,
                allocation_mm=total,constructed_analytic_length_mm=length+remaining,
                source_allocation_is_polyline=True,root_mm=fan[-1].tolist(),
                free_end_mm=q[-1].tolist()))
    return curves,infos


def ou_wire_stage(slot,done,curves,infos):
    """The growing active prefix is a subset of this full static route."""
    p=curves[slot];e=infos[slot]['curve_error_bound_mm'];ps=fine(p,.01)
    if infos[slot]['radius_status']!='PASS':
        return dict(status='BLOCKED',kind='fan_radius',detail=infos[slot])
    for target in rs_targets:
        margin=0. if target[0]=='Root_contact_bed_only' else .3
        hit=fc_wire_check(p,e,np.zeros(len(p)),target,margin)
        if hit:return dict(status='BLOCKED',kind='wire_structure',detail=hit)
    result=self_check(ps,e)
    if result['status']!='PASS':return dict(status='BLOCKED',kind='wire_self',detail=result)
    for other in range(4):
        result=own_prefix_check(ps,body_samples[other+1,0],e,body_error) if slot==other else pair(ps,body_samples[other+1,0],e,body_error)
        if result['status']!='PASS':return dict(status='BLOCKED',kind='wire_body',other=other,detail=result)
        if other==slot:continue
        q=curves[other] if other in done else ou_park[other]
        other_error=infos[other]['curve_error_bound_mm'] if other in done else 0.
        result=pair(ps,fine(q,.01),e,other_error)
        if result['status']!='PASS':return dict(status='BLOCKED',kind='wire_other',other=other,detail=result)
    return dict(status='PASS')


def ou_terminal_pose(slot,arc,dims):
    p=uf_curves[slot];s=uf_arcs[slot]
    rear=np.array([np.interp(arc,s,p[:,k]) for k in range(3)])
    eps=.002
    ahead=np.array([np.interp(min(s[-1],arc+eps),s,p[:,k]) for k in range(3)])
    behind=np.array([np.interp(max(0.,arc-eps),s,p[:,k]) for k in range(3)])
    t=ahead-behind;t/=np.linalg.norm(t)
    x=np.array([1.,0.,0.])-t*t[0]
    if np.linalg.norm(x)<1e-8:
        # All guide curves have nonnegative Z tangent. At the isolated -X
        # tangent, +Z is the one-sided limit of the projected +X frame.
        x=np.array([0.,0.,1.])-t*t[2]
    x/=np.linalg.norm(x);y=np.cross(t,x)
    rot=np.column_stack([x,y,t])
    return np.column_stack([rot,rear+t*dims[2]/2.]),rear


def ou_contact_check(slot,arc,done,dims,template):
    tr,rear=ou_terminal_pose(slot,arc,dims)
    solid=template.transform(tr);bb=np.array(solid.bounding_box());nearest=.301
    for name,group,m,lo,hi,_ in uf_targets:
        if np.any(bb[:3]>hi+.301) or np.any(bb[3:]<lo-.301):continue
        volume=max(0.,float((solid^m).volume()))
        gap=float(solid.min_gap(m,.301));nearest=min(nearest,gap)
        if volume>1e-7 or gap<.3:
            return dict(status='BLOCKED',kind='terminal_structure',object=name,
                gap_mm=gap,intersection_mm3=volume,rear_mm=rear.tolist(),
                transform_3x4=tr.tolist())
    obstacle=pw_obstacle('ordered_terminal','moving',solid)
    for other in range(4):
        if other==slot:
            end=max(0.,arc-2.)
            if end>0.:
                s=uf_arcs[other];p=uf_curves[other]
                boundary=np.array([np.interp(end,s,p[:,k]) for k in range(3)])
                q=np.vstack([p[s<end-1e-9],boundary]);e=uf_info[other]['curve_error_bound_mm']
            else:q=None;e=0.
        elif other in done:q=uf_curves[other];e=uf_info[other]['curve_error_bound_mm']
        else:q=ou_park[other];e=0.
        if q is not None:
            hit=fc_wire_check(q,e,np.zeros(len(q)),obstacle,0.)
            if hit:return dict(status='BLOCKED',kind='terminal_wire',other=other,detail=hit,rear_mm=rear.tolist())
        q=body_samples[other+1,0][0]
        if other==slot and arc<2.:
            s=body_samples[other+1,0][1];end=s[-1]-(2.-arc)
            boundary=np.array([np.interp(end,s,q[:,k]) for k in range(3)])
            q=np.vstack([q[s<end-1e-10],boundary])
        hit=fc_wire_check(q,body_error,np.zeros(len(q)),obstacle,0.)
        if hit:return dict(status='BLOCKED',kind='terminal_body',other=other,detail=hit,rear_mm=rear.tolist())
        if other!=slot:
            at=uf_curves[other][-1] if other in done else ou_park[other][-1]
            fixed=template.translate((at+np.array([0.,0.,dims[2]/2.])).tolist())
            volume=max(0.,float((solid^fixed).volume()))
            if volume>1e-7:return dict(status='BLOCKED',kind='terminal_terminal',other=other,intersection_mm3=volume)
            # Active final wire must also clear every parked contact, even
            # before the active contact reaches that region.
            q=uf_curves[slot]
            hit=fc_wire_check(q,uf_info[slot]['curve_error_bound_mm'],np.zeros(len(q)),
                             pw_obstacle('other_parked_terminal','fixed',fixed),0.)
            if hit:return dict(status='BLOCKED',kind='wire_parked_terminal',other=other,detail=hit)
    return dict(status='PASS',nearest_structure_capped_mm=nearest)


for label,dims in [('requested_space_only',[1.,1.8,4.1]),('old_nominal_box',[.8,1.35,3.9])]:
    selected=False
    for offset,dx in [(1.5,-.5),(1.8,-.5),(2.,-.5)]:
        uf_curves,uf_info=ou_make(offset,dx)
        uf_arcs=[np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))] for q in uf_curves]
        prefix=f'{label}_y{offset:g}_x{dx:g}'
        for slot,q in enumerate(uf_curves):ou_saved[f'{prefix}_slot{slot}']=q
        template=manifold.Manifold.cube(dims,center=True);done=[];stages=[]
        for slot in ou_order:
            wire=ou_wire_stage(slot,done,uf_curves,uf_info)
            row=dict(slot=slot,completed_slots=done.copy(),pending_slots=[j for j in ou_order if j!=slot and j not in done],wire_check=wire)
            if wire['status']!='PASS':
                row.update(status='BLOCKED',checked_positions=0);stages.append(row)
                print('ORDERED_FEED_WIRE',label,offset,dx,slot,wire,round(time.time()-ou_started,1),flush=True);break
            stations=np.linspace(0.,uf_arcs[slot][-1],int(math.ceil(uf_arcs[slot][-1]/ou_step))+1)
            outcome={'status':'PASS'};checked=0
            for arc in stations:
                checked+=1;outcome=ou_contact_check(slot,float(arc),done,dims,template)
                if outcome['status']!='PASS':outcome['arc_mm']=float(arc);break
            row.update(status=outcome['status'],contact_check=outcome,checked_positions=checked,
                       planned_positions=len(stations))
            stages.append(row)
            print('ORDERED_FEED_STAGE',label,offset,dx,slot,row['status'],checked,
                  outcome if outcome['status']!='PASS' else '',round(time.time()-ou_started,1),flush=True)
            if row['status']!='PASS':break
            done.append(slot)
        ok=len(done)==4
        ou_rows.append(dict(allocation=label,dimensions_mm=dims,root_offset_y_mm=offset,
            slot0_temporary_dx_mm=dx,status='PASS' if ok else 'BLOCKED',stages=stages,
            curves=uf_info,curve_key_prefix=prefix))
        if ok:selected=True;break

np.savez_compressed(OU_OUT/'curves.npz',**ou_saved)
report=dict(status='PASS' if any(r['status']=='PASS' for r in ou_rows) else 'BLOCKED',
    scope='Finite ordered upper terminal-feed screen with explicit pending and completed lead states',
    source_main_sha256=source_hash,script_sha256=sha(OU_SCRIPT),helper_sha256=sha(OU_HELPER),
    source_target_seating_sha256=sha(RX_OUT/'verification.json'),
    source_previous_guide_sha256=sha(UF_OUT/'screen.json'),
    wire_order=ou_order,wire_OD_mm=OD,station_step_upper_bound_mm=ou_step,
    structure_margin_mm=.3,terminal_wire_margin_mm=0.,wire_wire_margin_mm=.3,
    own_crimp_exclusion_mm=2.,pending_wire_height_mm=13.,
    source_fixture_ids=[t[0] for t in uf_targets],uninstalled_tie_parts=sorted(rs_omitted),
    source_allocation='Existing upper planned arclength, with fan length compensated in the free straight',
    rows=ou_rows,curves_sha256=sha(OU_OUT/'curves.npz'),
    continuous_feed='NOT_TESTED',guide_frame_twist='NOT_TESTED',
    connection_from_neck_stage='NOT_TESTED',body_end_material_supply='NOT_TESTED',
    return_to_final_upper_shape='NOT_TESTED',actual_terminal_profile='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-ou_started)
(OU_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ORDERED_FEED_DONE',report['status'],round(time.time()-ou_started,1),flush=True)
