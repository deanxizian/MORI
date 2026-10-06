"""Seat all four insulated leads laterally before the root tie is installed.

Keep the lower four fan endpoints fixed. Circular bends keep their radii;
Bezier spans retain both joining tangents. Extra fan length is taken from
the long straight free tail, not from stretching or changing the cut length.
This is a finite path screen, not proof of initial feeding or tie closure.
"""
from pathlib import Path
RS_SCRIPT=Path(__file__).resolve();RS_ROOT=RS_SCRIPT.parent
RS_HELPER=RS_ROOT/'check_CAM_sequential_continuous.py';__file__=str(RS_HELPER)
exec(compile(RS_HELPER.read_text().split('\n# Static mixed states',1)[0],str(RS_HELPER),'exec'),globals())
__file__=str(RS_SCRIPT)
RS_OUT=TC_OUT/'root_seating';RS_OUT.mkdir(exist_ok=True)
rs_started=time.time();rs_step=.008;rs_need=7.
rs_pool_file=RS_ROOT/'cam_fan_in/four_bend_transition/pool.json'
rs_pool=json.loads(rs_pool_file.read_text())
rs_candidates=[r['candidates'][0] for r in rs_pool['rows']]
rs_up=np.array([0.,0.,1.]);rs_gy,rs_gw=np.polynomial.legendre.leggauss(96)


def rs_split(c):
    levels=[np.array(c)]
    while len(levels[-1])>1:levels.append((levels[-1][:-1]+levels[-1][1:])/2)
    return np.array([x[0] for x in levels]),np.array([x[-1] for x in levels[::-1]])


def rs_bezier_bound(c,depth=0,tolerance=2e-5):
    v=3*np.diff(c,axis=0);a=6*np.diff(c,n=2,axis=0);cross=np.zeros((4,3))
    for i in range(3):
        for j in range(2):cross[i+j]+=math.comb(2,i)*math.comb(1,j)/math.comb(3,i+j)*np.cross(v[i],a[j])
    low=v.min(0);high=v.max(0)
    speed=float(np.linalg.norm(np.maximum(np.maximum(low,-high),0.)))
    radius=max(0.,speed-1e-12)**3/(float(np.linalg.norm(cross,axis=1).max())*(1+1e-9)+1e-20)
    chord=float(np.linalg.norm(c[-1]-c[0]));polygon=float(np.linalg.norm(np.diff(c,axis=0),axis=1).sum())
    if (radius>=rs_need and polygon-chord<=tolerance) or depth>=16:
        return dict(low=max(0.,chord-1e-10),high=polygon+1e-10,radius=radius,
            unresolved=int(radius<rs_need or polygon-chord>tolerance),intervals=1)
    p,q=rs_split(c);p=rs_bezier_bound(p,depth+1,tolerance/2);q=rs_bezier_bound(q,depth+1,tolerance/2)
    return dict(low=p['low']+q['low'],high=p['high']+q['high'],radius=min(p['radius'],q['radius']),
        unresolved=p['unresolved']+q['unresolved'],intervals=p['intervals']+q['intervals'])


def rs_bezier(c):
    n=max(2,int(math.ceil(3*float(np.linalg.norm(np.diff(c,axis=0),axis=1).max())/rs_step)))
    t=np.linspace(0,1,n+1);q=((1-t)**3)[:,None]*c[0]+(3*(1-t)**2*t)[:,None]*c[1]
    q+=(3*(1-t)*t*t)[:,None]*c[2]+(t**3)[:,None]*c[3]
    error=float(np.linalg.norm(6*np.diff(c,n=2,axis=0),axis=1).max())/(8*n*n)
    u=(rs_gy+1)/2;d=3*((1-u)**2)[:,None]*(c[1]-c[0])
    d+=6*(u*(1-u))[:,None]*(c[2]-c[1])+3*(u*u)[:,None]*(c[3]-c[2])
    length=float(np.dot(rs_gw/2,np.linalg.norm(d,axis=1)))
    bound=rs_bezier_bound(c)
    assert bound['low']-1e-9<=length<=bound['high']+1e-9
    return q,length,error,bound


def rs_sbend(start,axis,delta,radius):
    alpha=math.acos(1-delta/(2*radius));n=max(2,int(math.ceil(radius*alpha/rs_step)))
    a=np.linspace(0,alpha,n+1)
    first=start+radius*(1-np.cos(a))[:,None]*axis+radius*np.sin(a)[:,None]*rs_up
    a=np.linspace(alpha,0,n+1)
    second=first[-1]+radius*(np.cos(a)-math.cos(alpha))[:,None]*axis+radius*(math.sin(alpha)-np.sin(a))[:,None]*rs_up
    length=2*radius*alpha
    return np.vstack([first,second[1:]]),length,radius*(1-math.cos(alpha/(2*n)))


def rs_height(offset):
    c=rs_candidates[0];r=c['parameters']['radii_mm'][-1]
    delta=c['end_mm'][1]-c['parameters']['side_y_mm']
    return 2*r*(math.sin(math.acos(1-(delta+offset)/(2*r)))-math.sin(math.acos(1-delta/(2*r))))


def rs_fan(slot,offset):
    c=rs_candidates[slot];dz=rs_height(offset);shift=np.array([0.,offset,dz])
    pieces=[];length=0.;errors=[];bounds=[]
    if slot==0:
        point=np.array(c['start_mm']);p=c['parameters'];end=np.array(c['end_mm'])+shift
        deltas=[point[0]-p['side_x_mm'],p['side_y_mm']-point[1],end[0]-p['side_x_mm'],end[1]-p['side_y_mm']]
        axes=[[-1,0,0],[0,1,0],[1,0,0],[0,1,0]]
        for axis,delta,radius in zip(axes,deltas,p['radii_mm']):
            q,L,e=rs_sbend(point,np.array(axis),delta,radius)
            pieces.append(q);point=q[-1];length+=L;errors.append(e)
        line_length=float(end[2]-point[2]);assert line_length>0
        pieces.append(np.linspace(point,end,max(2,int(math.ceil(line_length/rs_step))+1)))
        length+=line_length;low=length-1e-8;high=length+1e-8;radius=min(p['radii_mm']);unresolved=0
    else:
        controls=[np.array(q) for q in c['controls_mm']]
        controls[-1][-2:]+=shift
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
    assert np.linalg.norm(q[0]-pw_fans[slot][0][0])<1e-8
    assert np.linalg.norm(q[-1]-(oe_static[slot,0.][0][0]+shift))<1e-8
    return q,length,max(errors),dict(length_lower_mm=low,length_upper_mm=high,
        minimum_radius_lower_mm=radius,radius_status='PASS' if not unresolved and radius>=rs_need else 'BLOCKED',
        unresolved_radius_or_length_intervals=unresolved)


rs_initial=[rs_fan(slot,0.) for slot in range(4)]
rs_root_box=box([float(xx.min()-1.2),-4.5,230.6],[float(xx.max()+1.2),-1.75,233.6])
rs_yoke=next(t[2] for t in fm_targets if t[0]=='Pitch_Yoke')
rs_bed=rs_yoke^rs_root_box;rs_rest=rs_yoke-rs_root_box
rs_diff=max(0.,float((rs_yoke-(rs_bed+rs_rest)).volume()))+max(0.,float(((rs_bed+rs_rest)-rs_yoke).volume()))
assert rs_diff<1e-7 and rs_bed.volume()>1.
rs_omitted={'CAM_Tie_Head','CAM_Tie_Band'}
rs_targets=[t for t in fm_targets if t[0] not in rs_omitted|{'Pitch_Yoke'}]
rs_targets += [pw_obstacle('Pitch_Yoke_without_root_bed','fixed',rs_rest),pw_obstacle('Root_contact_bed_only','fixed',rs_bed)]


def rs_curves(offset):
    curves=[];info=[];dz=rs_height(offset)
    for slot in range(4):
        fan,L,error,bound=rs_fan(slot,offset);difference=L-rs_initial[slot][1]
        free,original_u,free_error,_=oe_static[slot,0.]
        cut=5.;assert cut-difference>1.
        u=np.sort(np.unique(np.r_[cut,original_u[original_u>=cut]]))
        tail=np.column_stack([np.interp(u,original_u,free[:,k]) for k in range(3)])
        tail += np.array([0.,offset,dz-difference])
        straight=np.linspace(fan[-1],tail[0],max(2,int(math.ceil((cut-difference)/rs_step))+1))
        q=np.vstack([fan[:-1],straight[:-1],tail])
        e=max(error,free_error*2)
        bound.update(slot=slot,fan_length_mm=L,fan_length_change_mm=difference,
            free_straight_remaining_mm=cut-difference,whole_length_change_mm=L-rs_initial[slot][1]-difference,
            length_compensation_bound_mm=(bound['length_upper_mm']-bound['length_lower_mm'])+
                (rs_initial[slot][3]['length_upper_mm']-rs_initial[slot][3]['length_lower_mm']),
            root_mm=fan[-1].tolist(),free_end_mm=q[-1].tolist(),curve_error_bound_mm=e)
        curves.append(q);info.append(bound)
    return curves,info


def rs_check(offset):
    curves,info=rs_curves(offset);checks=[];samples=[fine(p,.01) for p in curves]
    errors=[r['curve_error_bound_mm'] for r in info];contacts=[]
    for slot in range(4):
        _,tr=ft_frame(0.,curves[slot][-1]);contacts.append(pw_obstacle(f'bare_contact_{slot}','free',ft_box.transform(tr)))
    for slot,p in enumerate(curves):
        if info[slot]['radius_status']!='PASS':return dict(status='BLOCKED',kind='radius',slot=slot,detail=info[slot]),curves,info
        for target in rs_targets:
            margin=0. if target[0]=='Root_contact_bed_only' else .3
            hit=fc_wire_check(p,errors[slot],np.zeros(len(p)),target,margin)
            if hit:return dict(status='BLOCKED',kind='wire_structure',slot=slot,detail=hit),curves,info
        self_result=self_check(samples[slot],errors[slot]);checks.append(dict(kind='self',slot=slot,**self_result))
        if self_result['status']!='PASS':return dict(status='BLOCKED',kind='self',slot=slot,detail=self_result),curves,info
        for other in range(4):
            result=own_prefix_check(samples[slot],body_samples[other+1,0],errors[slot],body_error) if other==slot else pair(samples[slot],body_samples[other+1,0],errors[slot],body_error)
            checks.append(dict(kind='body_prefix',slot=slot,other=other,**result))
            if result['status']!='PASS':return dict(status='BLOCKED',kind='body_prefix',slot=slot,other=other,detail=result),curves,info
            if other>slot:
                result=pair(samples[slot],samples[other],errors[slot],errors[other]);checks.append(dict(kind='other_wire',slot=slot,other=other,**result))
                if result['status']!='PASS':return dict(status='BLOCKED',kind='other_wire',slot=slot,other=other,detail=result),curves,info
        contact=contacts[slot];m=contact[2]
        for name,_,solid,lo,hi,_ in rs_targets:
            bb=np.array(m.bounding_box());required=.3001
            if np.any(bb[:3]>hi+required) or np.any(bb[3:]<lo-required):continue
            volume=max(0.,float((m^solid).volume()));gap=float(m.min_gap(solid,required+.001))
            if volume>1e-7 or gap<required:return dict(status='BLOCKED',kind='contact_structure',slot=slot,object=name,intersection_mm3=volume,gap_mm=gap),curves,info
        for other in range(4):
            q=curves[other]
            if other==slot:
                # Own crimp joins only the last 2 mm, which is a straight.
                zlimit=q[-1,2]-2.;q=q[q[:,2]<=zlimit]
                assert len(q)>0 and q[-1,2]<zlimit+.011
            hit=fc_wire_check(q,errors[other],np.zeros(len(q)),contact,0.)
            if hit:return dict(status='BLOCKED',kind='contact_wire',slot=slot,other=other,detail=hit),curves,info
            q=body_samples[other+1,0][0]
            hit=fc_wire_check(q,body_error,np.zeros(len(q)),contact,0.)
            if hit:return dict(status='BLOCKED',kind='contact_body',slot=slot,other=other,detail=hit),curves,info
            if other>slot and float((m^contacts[other][2]).volume())>1e-7:
                return dict(status='BLOCKED',kind='contact_contact',slots=[slot,other]),curves,info
    return dict(status='PASS',checks=checks),curves,info


rs_rows=[];rs_saved={}
for offset in [0.,1.5]+[float(x) for x in np.linspace(.075,1.425,19)]:
    outcome,curves,info=rs_check(offset)
    rs_rows.append(dict(offset_y_mm=offset,temporary_root_raise_mm=rs_height(offset),result=outcome,curves=info))
    if offset in [0.,.75,1.5]:
        for slot,p in enumerate(curves):rs_saved[f'offset{offset:g}_slot{slot}']=p
    print('ROOT_SEATING_POSITION',offset,outcome['status'],outcome.get('kind'),outcome.get('slot'),outcome.get('detail'),flush=True)
np.savez_compressed(RS_OUT/'seating_curves.npz',**rs_saved)
rs_status='PASS' if all(r['result']['status']=='PASS' for r in rs_rows) else 'BLOCKED'
report=dict(status=rs_status,scope='Finite prescribed lateral insulated-wire seating before fitting the root tie, at fixed yaw/pitch zero',
    source_main_sha256=source_hash,script_sha256=sha(RS_SCRIPT),helper_sha256=sha(RS_HELPER),
    source_fan_pool_sha256=sha(rs_pool_file),source_forming_sha256=sha(TC_OUT/'negative_complete/screen.json'),
    source_fixture_ids=[t[0] for t in fm_targets],uninstalled_root_tie_parts=sorted(rs_omitted),
    ordinary_wire_margin_mm=.3,functional_root_bed_margin_mm=0.,bed_split_difference_mm3=rs_diff,
    bed_split_scope='Exact Boolean partition only, no source material removed',
    root_frontward_offset_range_mm=[1.5,0.],wire_OD_mm=OD,required_radius_mm=rs_need,
    rows=rs_rows,curves_sha256=sha(RS_OUT/'seating_curves.npz'),
    constant_length_method='Exact circular spans and bounded Bezier arclength; compensate fan growth in a greater-than-1-mm remaining straight free segment',
    continuous_motion='NOT_TESTED',terminal_bypass_to_start='NOT_TESTED',tie_threading_and_tightening='NOT_TESTED',
    actual_contact_cad='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    elapsed_s=time.time()-rs_started)
(RS_OUT/'finite_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ROOT_SEATING_DONE',rs_status,len(rs_rows),round(time.time()-rs_started,2),flush=True)
