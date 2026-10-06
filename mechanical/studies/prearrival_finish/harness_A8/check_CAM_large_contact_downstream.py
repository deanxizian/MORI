"""Replay the larger requested contact allocation through later CAM steps.

This independent finite diagnostic changes neither a route nor a source solid.
The 1 x 1.8 x 4.1 mm box is ASSUMED requested space, not a manufacturer's
finished/crimped terminal envelope. Earlier small-box receipts stay intact.
"""
from pathlib import Path

LC_SCRIPT=Path(__file__).resolve();LC_ROOT=LC_SCRIPT.parent
LC_HELPER=LC_ROOT/'refine_CAM_root_seating.py';__file__=str(LC_HELPER)
exec(compile(LC_HELPER.read_text().split('\nrx_rows=[];',1)[0],str(LC_HELPER),'exec'),globals())
__file__=str(LC_SCRIPT)
LC_OUT=RS_OUT/'large_contact_downstream';LC_OUT.mkdir(exist_ok=True)
lc_started=time.time();lc_rows=[];lc_saved={}
lc_seat_path=RX_OUT/'verification.json'
lc_forming_path=TC_OUT/'negative_complete/screen.json'
lc_recovery_path=RS_OUT/'ordered_feed_recovery/screen.json'
lc_seat=json.loads(lc_seat_path.read_text());lc_forming=json.loads(lc_forming_path.read_text())
lc_recovery=json.loads(lc_recovery_path.read_text())
assert lc_seat['status']==lc_forming['status']==lc_recovery['status']=='PASS'
assert lc_forming['source_main_sha256']==lc_recovery['source_main_sha256']==source_hash
ft_dims=np.array([1.,1.8,4.1]);ft_box=manifold.Manifold.cube(ft_dims,center=True)
lc_static={}
for slot in range(4):
    for phase in (0.,1.):
        st_angle_max=0.
        _,transform=ft_frame(phase,oe_static[slot,phase][0][-1])
        lc_static[slot,phase]=pw_obstacle(f'allocated_static_contact_{slot}_{phase}','fixed',ft_box.transform(transform))


def lc_contacts_check(curves,errors,contacts,targets,upstream,own_masks):
    """Check all contacts, all wires, and all fixed structure at one pose."""
    for slot,contact in enumerate(contacts):
        shape=contact[2];bounds=np.array(shape.bounding_box())
        for name,_,solid,lower,upper,_ in targets:
            if np.any(bounds[:3]>upper+.301) or np.any(bounds[3:]<lower-.301):continue
            volume=max(0.,float((shape^solid).volume()));gap=float(shape.min_gap(solid,.301))
            if volume>1e-7 or gap<.3-1e-6:
                return dict(kind='contact_structure',slot=slot,object=name,gap_mm=gap,intersection_mm3=volume)
        for other,q in enumerate(curves):
            local=own_masks[slot](q) if other==slot else q
            hit=fc_wire_check(local,errors[other],np.zeros(len(local)),contact,0.)
            if hit:return dict(kind='contact_wire',slot=slot,other_slot=other,detail=hit)
        for label,q,error in upstream:
            hit=fc_wire_check(q,error,np.zeros(len(q)),contact,0.)
            if hit:return dict(kind='contact_upstream',slot=slot,other=label,detail=hit)
        for other in range(slot+1,4):
            volume=max(0.,float((shape^contacts[other][2]).volume()))
            if volume>1e-7:
                return dict(kind='contact_contact',slot=slot,other_slot=other,intersection_mm3=volume)
    return None


def lc_root_pose(offset):
    global st_angle_max
    st_angle_max=0.;curves,info=rs_curves(offset);contacts=[];masks=[]
    for slot,q in enumerate(curves):
        _,transform=ft_frame(0.,q[-1])
        contacts.append(pw_obstacle(f'allocated_root_contact_{slot}','moving',ft_box.transform(transform)))
        def mask(p):
            boundary=p[-1].copy();boundary[2]-=2.
            return np.vstack([p[p[:,2]<boundary[2]-1e-10],boundary])
        masks.append(mask)
    errors=[r['curve_error_bound_mm']+r['length_compensation_bound_mm'] for r in info]
    upstream=[(f'body_{i}',body_samples[i+1,0][0],body_error) for i in range(4)]
    failure=lc_contacts_check(curves,errors,contacts,rs_targets,upstream,masks)
    return failure,curves,contacts


def lc_forming_pose(stage,edge,fraction):
    global st_angle_max
    active=da_order[stage]
    p,u,error=sc_curve(stage,edge,fraction)
    _,transform=ft_frame(fraction,p[-1])
    moving=pw_obstacle('allocated_active_contact','moving',ft_box.transform(transform))
    curves=[];errors=[];contacts=[];masks=[]
    for slot in range(4):
        if slot==active:
            q,v,e=p,u,error;contact=moving
        else:
            phase=1. if da_order.index(slot)<stage else 0.
            q,v,e,_=oe_static[slot,phase];contact=lc_static[slot,phase]
        # Include the exact two-millimetre own-crimp boundary for every strand.
        new_u=np.sort(np.unique(np.r_[v,fc_end-2.]))
        q=np.column_stack([np.interp(new_u,v,q[:,axis]) for axis in range(3)])
        keep=new_u<=fc_end-2.+1e-10
        masks.append(lambda points,keep=keep:points[keep])
        curves.append(q);errors.append(2.*e);contacts.append(contact)
    upstream=[]
    for slot in range(4):
        upstream.extend([(f'fan_{slot}',pw_fans[slot][0],pw_fan_errors[slot]),
                         (f'body_{slot}',body_samples[slot+1,0][0],body_error)])
    failure=lc_contacts_check(curves,errors,contacts,fm_targets,upstream,masks)
    return failure,curves,contacts


def lc_record(kind,parameters,failure,curves,contacts):
    row=dict(step=kind,**parameters,status='PASS' if failure is None else 'BLOCKED',failure=failure)
    lc_rows.append(row)
    if failure:
        key=f'{kind}_{len(lc_rows)}'
        for slot,q in enumerate(curves):lc_saved[f'{key}_wire{slot}']=q
        for slot,c in enumerate(contacts):
            mesh=c[2].to_mesh();lc_saved[f'{key}_contact{slot}_vertices']=np.array(mesh.vert_properties)[:,:3]
            lc_saved[f'{key}_contact{slot}_triangles']=np.array(mesh.tri_verts)
    return row


for offset in np.linspace(1.5,0.,21):
    failure,curves,contacts=lc_root_pose(float(offset))
    lc_record('root_seating',dict(offset_y_mm=float(offset)),failure,curves,contacts)
    print('LARGER_ROOT',float(offset),'PASS' if failure is None else failure,flush=True)

# A failure stops that stage's finite replay: don't waste a continuous run on
# a demonstrably unproved route, and don't imply that unvisited poses passed.
lc_stage_rows=[]
for stage_data in lc_forming['stages']:
    stage=stage_data['stage'];path=stage_data['path'];tested=0;failure=None
    for a,b in zip(path,path[1:]):
        for f in np.linspace(a['fraction'],b['fraction'],5):
            failure,curves,contacts=lc_forming_pose(stage,(a,b),float(f));tested+=1
            row=lc_record('forming',dict(stage=stage,geometric_slot=da_order[stage],fraction=float(f),
                amplitude_mm=sc_control((a,b),f)[0],side_angle_deg=sc_control((a,b),f)[1]),failure,curves,contacts)
            if failure:break
        if failure:break
    lc_stage_rows.append(dict(stage=stage,status='PASS' if failure is None else 'BLOCKED',
        checked_positions=tested,first_failure=row if failure else None))
    print('LARGER_FORMING_STAGE',stage,tested,'PASS' if failure is None else failure,flush=True)

np.savez_compressed(LC_OUT/'failure_poses.npz',**lc_saved)
status='PASS' if all(r['status']=='PASS' for r in lc_rows) else 'BLOCKED'
report=dict(status=status,scope='Finite replay of the larger ASSUMED contact space through existing root seating and four-stage forming; unchanged route and source solids',
    script_sha256=sha(LC_SCRIPT),helper_sha256=sha(LC_HELPER),source_main_sha256=source_hash,
    source_seating_sha256=sha(lc_seat_path),source_forming_sha256=sha(lc_forming_path),
    source_recovery_sha256=sha(lc_recovery_path),contact_dimensions_mm=ft_dims.tolist(),
    contact_evidence='ASSUMED requested space; no manufacturer post-crimp maximum envelope established',
    root_seating_positions=21,forming_stages=lc_stage_rows,rows=lc_rows,
    contact_structure_margin_mm=.3,contact_wire_margin_mm=0.,contact_contact_scope='Nominal nonpenetration only; zero-volume touching allowed; no manufacturing clearance claim',
    own_crimp_exclusion_mm=2.,own_crimp_boundary_inserted=True,
    failure_poses_sha256=sha(LC_OUT/'failure_poses.npz'),continuous_motion='NOT_TESTED',
    earlier_small_box_results_superseded=False,actual_terminal_fit='NOT_TESTED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-lc_started)
(LC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LARGER_DOWNSTREAM_DONE',status,len(lc_rows),round(time.time()-lc_started,2),flush=True)
