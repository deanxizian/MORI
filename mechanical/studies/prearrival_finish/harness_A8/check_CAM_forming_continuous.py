"""Conservative continuous bounds for one constant-length forming candidate.

At a fixed planar arclength coordinate the X quintic is fixed, so that
coordinate also labels fixed material along the 3D wire. The integral of
the tangent-angle derivative bounds motion at every coordinate. No temporal
sampling is promoted to continuous evidence without this displacement bound.

The existing CAM grooved bed is checked at the real wire radius for the
final 5mm seating straight, instead of excluding that straight altogether.
All other noncontact checks retain 0.3mm nominal surface clearance.
"""
from pathlib import Path
FC_SCRIPT=Path(__file__).resolve();FC_ROOT=FC_SCRIPT.parent
FC_HELPER=FC_ROOT/'check_CAM_forming_terminals.py';__file__=str(FC_HELPER)
exec(compile(FC_HELPER.read_text().split('\nfor fraction in np.linspace',1)[0],str(FC_HELPER),'exec'),globals())
__file__=str(FC_SCRIPT)
FC_OUT=FM_OUT/'continuous';FC_OUT.mkdir(exist_ok=True)
fc_raised=json.loads((FM_OUT/'raised/screen.json').read_text())
fc_terminal=json.loads((FM_OUT/'terminals/screen.json').read_text())
assert fc_raised['status']==fc_terminal['status']=='PASS'
fc_amplitude=float(fc_raised['selected_amplitude_mm'])
fm_step=.01
fc_started=time.time();fc_tests=0;fc_passed=[];fc_unproved=[];fc_max_depth=19
fc_end=float(sum(fr_lengths));fc_seat_start=fc_end-5.
fc_bed=pw_readsolid(WI_ANCHOR/'z212.0_bed.npz')
fc_cradle=next(t[2] for t in fm_targets if t[0]=='Pitch_Cradle')
fc_actual_bed=fc_cradle^fc_bed;fc_rest=fc_cradle-fc_bed
assert abs((fc_actual_bed+fc_rest).volume()-fc_cradle.volume())<1e-6
assert max(0.,((fc_actual_bed+fc_rest)-fc_cradle).volume())<1e-7
assert max(0.,(fc_cradle-(fc_actual_bed+fc_rest)).volume())<1e-7
fc_targets=[t for t in fm_targets if t[0]!='Pitch_Cradle']+[
    pw_obstacle('Pitch_Cradle_without_CAM_bed','fixed',fc_rest),
    pw_obstacle('CAM_bed_only','fixed',fc_actual_bed)]
fc_root_contacts={'Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band'}
fc_B=float(sum(fr_lengths[:3]));fc_C=float(sum(fr_lengths[:6]))
fc_h0=float(fr_lengths[0]);fc_R=float(wi_rt);fc_r=float(fm_R)
fc_min_contact=2.;fc_min_seat_bound=math.inf


def fc_integrated_ramp(u,start,radius,turn):
    v=np.maximum(u-start,0.);end=np.maximum(v-radius*turn,0.)
    return (v*v-end*end)/(2.*radius)


def fc_speed(u,a,b):
    # theta=f*Theta(u,H(f)), H=h0+A*sin(pi*f).
    # Only the upper turn moves with H. Its arclength is pi*R; the following
    # return straight absorbs the displacement, so both lower turns are at
    # fixed material coordinates B and C. Integrating |theta_f| gives:
    hmin=fc_h0+fc_amplitude*min(math.sin(math.pi*a),math.sin(math.pi*b))
    integral=fc_integrated_ramp(u,hmin,fc_R,math.pi)
    integral+=fc_integrated_ramp(u,fc_B,fc_r,math.pi/2.)
    integral+=fc_integrated_ramp(u,fc_C,fc_r,math.pi/2.)
    hp=fc_amplitude*math.pi*max(abs(math.cos(math.pi*a)),abs(math.cos(math.pi*b)))
    moving_length=np.minimum(np.maximum(u-hmin,0.),math.pi*fc_R)
    return integral+b*hp/fc_R*moving_length


def fc_curve(fraction):
    # Insert exact contact-boundary coordinates so neither side is dropped.
    extra=fc_amplitude*math.sin(math.pi*fraction);lengths=np.array(fr_lengths,float)
    lengths[0]+=extra;lengths[2]-=extra;assert lengths.min()>.49
    bounds=np.r_[0.,np.cumsum(lengths)]
    knots=sorted(set(bounds.tolist()+[4.3,fc_seat_start]))
    u=np.r_[np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/fm_step))+1)[:-1]
                            for a,b in zip(knots,knots[1:])]),bounds[-1]]
    points=np.zeros((len(u),3));points[:,0]=xx[0]
    origin=np.array([-1.5,230.]);theta=0.
    for i,(length,turn) in enumerate(zip(lengths,fm_angles)):
        ids=np.flatnonzero((u>=bounds[i]-1e-10)&(u<=bounds[i+1]+1e-10));v=u[ids]-bounds[i]
        k=fraction*turn/length
        if abs(k)<1e-12:delta=np.c_[v*math.sin(theta),v*math.cos(theta)]
        else:delta=np.c_[(math.cos(theta)-np.cos(theta+k*v))/k,(np.sin(theta+k*v)-math.sin(theta))/k]
        points[ids,1:]=origin+delta
        if abs(k)<1e-12:origin+=length*np.array([math.sin(theta),math.cos(theta)])
        else:origin+=np.array([(math.cos(theta)-math.cos(theta+k*length))/k,(math.sin(theta+k*length)-math.sin(theta))/k])
        theta+=fraction*turn
    w=np.clip((fm_tail_parameter-(u-fm_core_length))/16.,0.,1.)
    points[:,0]=slots[0,0]+1.8875*(10*w**3-15*w**4+6*w**5)
    acceleration=fraction/min(fc_R,fc_r)+(10*math.sqrt(3)/3)*1.8875/16.**2
    return points,u,acceleration*fm_step**2/8.


def fc_wire_check(points,error,temporal,target,margin):
    global fc_min_seat_bound
    name,group,m,lo,hi,tree=target
    ds=np.linalg.norm(np.diff(points,axis=0),axis=1)
    if not len(ds):ds=np.zeros(1);points=np.vstack([points,points]);temporal=np.r_[temporal,temporal]
    space=np.maximum(np.r_[ds[0],ds],np.r_[ds,ds[-1]])/2.+error+1e-4
    allowance=OD/2.+margin+space+temporal
    ids=np.flatnonzero(np.all(points>=lo-allowance[:,None],axis=1)&np.all(points<=hi+allowance[:,None],axis=1))
    for i in ids:
        distance=float(tree.find_nearest(Vector(points[i]))[3])
        if distance<allowance[i]:return {'object':name,'point_mm':points[i].tolist(),'distance_mm':distance,
            'required_mm':float(allowance[i]),'temporal_mm':float(temporal[i]),'nominal_margin_mm':margin}
        if name=='CAM_bed_only' and margin==0.:
            fc_min_seat_bound=min(fc_min_seat_bound,distance-OD/2.-space[i]-temporal[i])
    # Surface distance is unsigned: exclude a path contained inside a solid.
    for i in (ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []):
        p=points[i]
        if np.all(p>=lo) and np.all(p<=hi):
            tiny=manifold.Manifold.sphere(.01,16).translate(p.tolist())
            if (tiny^m).volume()>tiny.volume()/2.:return {'object':name,'point_mm':p.tolist(),'inside':True}
    return None


def fc_test(a,b):
    global fc_min_contact
    f=(a+b)/2.;half=(b-a)/2.;base,u,error=fc_curve(f)
    temporal=fc_speed(u,a,b)*half
    # Bound every contact point by endpoint translation plus exact angular
    # velocity 2*pi and its distance from the wire-exit rotation axis.
    radial=math.hypot(ft_dims[1]/2.,ft_dims[2])
    contact_motion=(float(fc_speed(np.array([fc_end]),a,b)[0])+2.*math.pi*radial)*half
    nearest=2.+contact_motion
    for slot in range(4):
        rear=base[-1]+[xx[slot]-xx[0],0.,0.];rot,tr=ft_frame(f,rear);contact=ft_box.transform(tr)
        for name,group,m,lo,hi,tree in fm_targets:
            bb=np.array(contact.bounding_box());bound=.3+contact_motion+1e-4
            if np.any(bb[:3]>hi+bound) or np.any(bb[3:]<lo-bound):continue
            v=max(0.,float((contact^m).volume()))
            if v>1e-7:return {'kind':'contact','slot':slot,'object':name,'intersection_mm3':v}
            gap=float(contact.min_gap(m,bound+.001))
            if gap<bound:return {'kind':'contact','slot':slot,'object':name,'gap_mm':gap,'required_mm':bound,'temporal_mm':contact_motion}
            nearest=min(nearest,gap-contact_motion)
    fc_min_contact=min(fc_min_contact,nearest)
    for slot in range(4):
        points=base+[xx[slot]-xx[0],0.,0.]
        for target in fc_targets:
            name=target[0]
            if name in fc_root_contacts:pieces=[(u>=4.3-1e-9,.3)]
            elif name=='CAM_bed_only':pieces=[(u<=fc_seat_start+1e-9,.3),(u>=fc_seat_start-1e-9,0.)]
            else:pieces=[(np.ones(len(u),bool),.3)]
            for keep,margin in pieces:
                hit=fc_wire_check(points[keep],error,temporal[keep],target,margin)
                if hit:return {'kind':'wire','slot':slot,**hit}
    return None


def fc_interval(a,b,depth=0):
    global fc_tests
    fc_tests+=1;hit=fc_test(a,b)
    if hit and depth<fc_max_depth:
        mid=(a+b)/2.;fc_interval(a,mid,depth+1);fc_interval(mid,b,depth+1)
    elif hit:
        fc_unproved.append({'interval':[a,b],'failure':hit})
        print('FORMING_UNPROVED',a,b,hit,flush=True)
    else:
        fc_passed.append({'interval':[a,b],'status':'PASS'})
        if len(fc_passed)%20==0:print('FORMING_CONTINUOUS',len(fc_passed),round(b,6),'tests',fc_tests,'sec',round(time.time()-fc_started,1),flush=True)
    # Persist partial diagnostics on any repeated true obstruction; this
    # boundary is a bounded audit, not a potentially million-cell search.
    if len(fc_unproved)>30:raise RuntimeError('More than30 unresolved intervals; inspect saved progress before continuing')


try:
    fc_interval(0.,1.)
    fc_error=None
except Exception as e:
    fc_error=repr(e)
allrows=sorted(fc_passed+fc_unproved,key=lambda r:r['interval'][0])
coverage=bool(allrows and allrows[0]['interval'][0]==0. and allrows[-1]['interval'][1]==1.
              and all(a['interval'][1]==b['interval'][0] for a,b in zip(allrows,allrows[1:])))
report={'status':'PASS' if coverage and not fc_unproved and not fc_error else 'BLOCKED',
 'scope':'Continuous prescribed four-wire and catalogue bare contact clearance to forming-stage solids; not full harness',
 'source_main_sha256':source_hash,'script_sha256':sha(FC_SCRIPT),'helper_sha256':sha(FC_HELPER),
 'source_raised_screen_sha256':sha(FM_OUT/'raised/screen.json'),'source_terminal_screen_sha256':sha(FM_OUT/'terminals/screen.json'),'amplitude_mm':fc_amplitude,
 'passed_intervals':fc_passed,'unproved_intervals':fc_unproved,'interval_tests':fc_tests,'complete_coverage':coverage,'error':fc_error,
 'wire_OD_mm':OD,'ordinary_surface_margin_mm':.3,'wire_chord_parameter_step_mm':fm_step,
 'seating_surface':'Only existing z212 grooved CAM bed and final5mm material straight; full wire radius checked, no omission',
 'seating_nonpenetration_margin_mm':0.,'minimum_seating_gap_lower_bound_mm':fc_min_seat_bound if math.isfinite(fc_min_seat_bound) else None,
 'minimum_contact_gap_lower_bound_mm':fc_min_contact,
 'velocity_bound':'Integral of Theta at minimum H plus b*sup(abs(Hprime))/R times covered upper-turn length; angular contact bound2*pi*r',
 'unchanged_yaw_contact':'First4.3mm fixed straight reused from prior anchor check',
 'wire_to_wire':'NOT_TESTED','wire_to_contact':'NOT_TESTED','terminal_to_housing_insertion':'NOT_TESTED',
 'initial_feed_to_upright_state':'NOT_TESTED','tie_threading_tightening':'NOT_TESTED',
 'source_solids_considered':len(fm_targets),'uninstalled_CAM_board':True,'untightened_tie_final_solids_omitted':sorted(fm_deferred),
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-fc_started}
(FC_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FORMING_CONTINUOUS_DONE',report['status'],len(fc_passed),len(fc_unproved),fc_error,flush=True)
