"""Keep the ordered feed but translate the temporary four-lane fan together.

The previous leftward shift was toward the pitch-servo body. Check a common
rightward temporary guide offset instead, preserving wire spacing. Optional
smooth contact-roll schedules use the narrow side at the two servo passages.
This remains an independent finite guide/assembly study, not a source edit.
"""
from pathlib import Path
SF_SCRIPT=Path(__file__).resolve();SF_ROOT=SF_SCRIPT.parent
SF_HELPER=SF_ROOT/'plan_CAM_ordered_upper_feed.py';__file__=str(SF_HELPER)
exec(compile(SF_HELPER.read_text().split('\nfor label,dims in ',1)[0],str(SF_HELPER),'exec'),globals())
__file__=str(SF_SCRIPT)
import os
SF_HANDLE=float(os.environ.get('MORI_CAM_UPPER_HANDLE_MM','0'))
assert SF_HANDLE in (0.,.5)
SF_OUT=RS_OUT/('shifted_ordered_feed' if not SF_HANDLE else 'shifted_ordered_feed_handle05');SF_OUT.mkdir(exist_ok=True)
sf_started=time.time();sf_rows=[];sf_saved={};sf_roll_mode=0
sf_pose_without_roll=ou_terminal_pose


def ou_fan(slot,offset,dx):
    c=ou_original_candidates[slot];shift=np.array([dx,offset,rs_height(offset)])
    pieces=[];length=0.;errors=[];bounds=[]
    if slot==0:
        p=c['parameters'];point=np.array(c['start_mm']);end=np.array(c['end_mm'])+shift
        deltas=[point[0]-p['side_x_mm'],p['side_y_mm']-point[1],end[0]-p['side_x_mm'],end[1]-p['side_y_mm']]
        for axis,delta,radius in zip([[-1,0,0],[0,1,0],[1,0,0],[0,1,0]],deltas,p['radii_mm']):
            q,L,e=rs_sbend(point,np.array(axis),delta,radius)
            pieces.append(q);point=q[-1];length+=L;errors.append(e)
        dz=float(end[2]-point[2])
        if dz<0.:
            # Preserve the circular tangents and use the natural taller fan
            # end; a higher temporary free-tail datum is allowed at this stage.
            end=point.copy();dz=0.
        if dz>1e-10:pieces.append(np.linspace(point,end,max(2,int(math.ceil(dz/rs_step))+1)))
        length+=dz;low=length-1e-8;high=length+1e-8;radius=min(p['radii_mm']);unresolved=0
    else:
        controls=[np.array(q) for q in c['controls_mm']];controls[-1][-2:]+=shift
        if slot==3:controls[-1][-2,0]+=SF_HANDLE
        for ctrl in controls:
            q,L,e,b=rs_bezier(ctrl);pieces.append(q);length+=L;errors.append(e);bounds.append(b)
        low=sum(b['low'] for b in bounds);high=sum(b['high'] for b in bounds)
        radius=min(b['radius'] for b in bounds);unresolved=sum(b['unresolved'] for b in bounds)
        if c.get('arc'):
            arc=c['arc'];r=arc['radius_mm'];angle=arc['angle_rad'];start=np.array(arc['start_mm'])+shift
            n=max(2,int(math.ceil(r*angle/rs_step)));a=np.linspace(0,angle,n+1)
            q=start+np.column_stack([-r*np.sin(a),np.zeros(len(a)),r*(1-np.cos(a))])
            pieces.append(q);L=r*angle;length+=L;low+=L;high+=L;radius=min(radius,r)
            errors.append(r*(1-math.cos(angle/(2*n))))
    q=np.vstack([p[:-1] for p in pieces[:-1]]+[pieces[-1]])
    assert np.linalg.norm(q[0]-ou_target_curves[slot][0])<1e-8
    return q,length,max(errors),dict(length_lower_mm=low,length_upper_mm=high,
        minimum_radius_lower_mm=radius,radius_status='PASS' if not unresolved and radius>=rs_need else 'BLOCKED',
        unresolved_radius_or_length_intervals=unresolved)


def sf_ramp(z,lo,hi):
    u=float(np.clip((z-lo)/(hi-lo),0.,1.));return u*u*(3.-2.*u)


def ou_terminal_pose(slot,arc,dims):
    tr,rear=sf_pose_without_roll(slot,arc,dims);a=0.
    if sf_roll_mode and slot==0:
        a=90.*sf_ramp(rear[2],197.,202.)*(1.-sf_ramp(rear[2],210.,217.))
    elif sf_roll_mode and slot==2:
        a=90.*sf_ramp(rear[2],208.,215.)*(1.-sf_ramp(rear[2],219. if sf_roll_mode==1 else 222.,225. if sf_roll_mode==1 else 228.))
    r=math.radians(a);spin=np.array([[math.cos(r),-math.sin(r),0.],[math.sin(r),math.cos(r),0.],[0.,0.,1.]])
    tr[:,:3]=tr[:,:3]@spin
    return tr,rear


sf_bounds={n:[lo.tolist(),hi.tolist()] for n,g,m,lo,hi,t in uf_targets if n in ['Pitch_Servo','Yaw_Servo','Pitch_Yoke']}
print('ORDERED_GUIDE_BOUNDS',sf_bounds,flush=True)
for label,dims in [('requested_space_only',[1.,1.8,4.1]),('old_nominal_box',[.8,1.35,3.9])]:
    for offset,dx,mode in [(1.5,.2,0),(1.5,.2,1),(1.8,.2,1),(1.8,.2,2)]:
        sf_roll_mode=mode;uf_curves,uf_info=ou_make(offset,dx)
        uf_arcs=[np.r_[0.,np.cumsum(np.linalg.norm(np.diff(q,axis=0),axis=1))] for q in uf_curves]
        prefix=f'{label}_y{offset:g}_x{dx:g}_roll{mode}'
        for slot,q in enumerate(uf_curves):sf_saved[f'{prefix}_slot{slot}']=q
        template=manifold.Manifold.cube(dims,center=True);done=[];stages=[]
        for slot in ou_order:
            wire=ou_wire_stage(slot,done,uf_curves,uf_info)
            row=dict(slot=slot,completed_slots=done.copy(),pending_slots=[j for j in ou_order if j!=slot and j not in done],wire_check=wire)
            if wire['status']!='PASS':
                row.update(status='BLOCKED',checked_positions=0);stages.append(row)
                print('SHIFTED_FEED_WIRE',label,offset,dx,mode,slot,wire,round(time.time()-sf_started,1),flush=True);break
            stations=np.linspace(0.,uf_arcs[slot][-1],int(math.ceil(uf_arcs[slot][-1]/ou_step))+1)
            outcome={'status':'PASS'};checked=0
            for arc in stations:
                checked+=1;outcome=ou_contact_check(slot,float(arc),done,dims,template)
                if outcome['status']!='PASS':outcome['arc_mm']=float(arc);break
            row.update(status=outcome['status'],contact_check=outcome,checked_positions=checked,planned_positions=len(stations))
            stages.append(row)
            print('SHIFTED_FEED_STAGE',label,offset,dx,mode,slot,row['status'],checked,
                outcome if outcome['status']!='PASS' else '',round(time.time()-sf_started,1),flush=True)
            if row['status']!='PASS':break
            done.append(slot)
        ok=len(done)==4
        sf_rows.append(dict(allocation=label,dimensions_mm=dims,root_offset_y_mm=offset,
            common_temporary_dx_mm=dx,roll_mode=mode,status='PASS' if ok else 'BLOCKED',
            stages=stages,curves=uf_info,curve_key_prefix=prefix))
        if ok:break

np.savez_compressed(SF_OUT/'curves.npz',**sf_saved)
report=dict(status='PASS' if any(r['status']=='PASS' for r in sf_rows) else 'BLOCKED',
    scope='Finite ordered feed with temporary common X offset and declared contact rolls',
    source_main_sha256=source_hash,script_sha256=sha(SF_SCRIPT),helper_sha256=sha(SF_HELPER),
    source_target_seating_sha256=sha(RX_OUT/'verification.json'),
    previous_ordered_feed_sha256=sha(OU_OUT/'screen.json'),wire_order=ou_order,wire_OD_mm=OD,
    slot3_incoming_handle_extension_mm=SF_HANDLE,
    station_step_upper_bound_mm=ou_step,structure_margin_mm=.3,terminal_wire_margin_mm=0.,
    wire_wire_margin_mm=.3,own_crimp_exclusion_mm=2.,pending_wire_height_mm=13.,
    source_fixture_ids=[t[0] for t in uf_targets],diagnostic_fixture_bounds_mm=sf_bounds,
    uninstalled_tie_parts=sorted(rs_omitted),rows=sf_rows,
    curves_sha256=sha(SF_OUT/'curves.npz'),continuous_feed='NOT_TESTED',
    guide_frame_twist='NOT_TESTED',connection_from_neck_stage='NOT_TESTED',
    body_end_material_supply='NOT_TESTED',return_to_final_upper_shape='NOT_TESTED',
    actual_terminal_profile='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-sf_started)
(SF_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('SHIFTED_FEED_DONE',report['status'],round(time.time()-sf_started,1),flush=True)
