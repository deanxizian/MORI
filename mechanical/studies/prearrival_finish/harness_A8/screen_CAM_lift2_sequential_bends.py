"""Finite candidate: form the tail's two quarter bends before the main U.

This changes only a temporary assembly motion. The complete centreline
length and installed endpoints remain constant. Previous simultaneous-turn
continuous bounds do not apply to this separately sequenced path.
"""
from pathlib import Path
SQ_SCRIPT=Path(__file__).resolve();SQ_ROOT=SQ_SCRIPT.parent
SQ_HELPER=SQ_ROOT/'screen_CAM_lift2_forming_apex.py';__file__=str(SQ_HELPER)
exec(compile(SQ_HELPER.read_text().split('\nap_order=',1)[0],str(SQ_HELPER),'exec'),globals())
__file__=str(SQ_SCRIPT)
SQ_OUT=L2_OUT/'sequential_bends';SQ_OUT.mkdir(exist_ok=True);sq_started=time.time()
sq_frame_original=ft_frame


def sq_controls(t):return max(0.,2*t-1.),min(1.,2*t)


def fc_curve(t):
    main,tail=sq_controls(t);extra=fc_amplitude*math.sin(math.pi*main)
    lengths=np.array(fr_lengths,float);lengths[0]+=extra;lengths[2]-=extra
    assert lengths.min()>.49
    bounds=np.r_[0.,np.cumsum(lengths)]
    knots=sorted(set(bounds.tolist()+[4.3,fc_seat_start,fc_seat_end]))
    u=np.r_[np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/fm_step))+1)[:-1]
        for a,b in zip(knots,knots[1:])]),bounds[-1]]
    points=np.zeros((len(u),3));origin=np.array([-1.5,230.]);theta=0.
    factors=[0.,main,0.,tail,0.,0.,tail,0.]
    for i,(length,turn,factor) in enumerate(zip(lengths,fm_angles,factors)):
        ids=np.flatnonzero((u>=bounds[i]-1e-10)&(u<=bounds[i+1]+1e-10));v=u[ids]-bounds[i]
        k=factor*turn/length
        if abs(k)<1e-12:delta=np.c_[v*math.sin(theta),v*math.cos(theta)]
        else:delta=np.c_[(math.cos(theta)-np.cos(theta+k*v))/k,(np.sin(theta+k*v)-math.sin(theta))/k]
        points[ids,1:]=origin+delta
        if abs(k)<1e-12:origin+=length*np.array([math.sin(theta),math.cos(theta)])
        else:origin+=np.array([(math.cos(theta)-math.cos(theta+k*length))/k,(math.sin(theta+k*length)-math.sin(theta))/k])
        theta+=factor*turn
    w=np.clip((fm_tail_parameter-(u-fm_core_length))/16.,0.,1.)
    points[:,0]=slots[0,0]+1.8875*(10*w**3-15*w**4+6*w**5)
    acc=max(main/fc_R,tail/fc_r)+(10*math.sqrt(3)/3)*1.8875/16.**2
    return points,u,acc*fm_step**2/8.


def ft_frame(t,rear):
    main,tail=sq_controls(t)
    return sq_frame_original((main+tail)/2.,rear)


sq_order=list(dict.fromkeys([.9,.8875,.9125,.875,.925,.85,.95,1.,.5,0.]+[round(float(x),8) for x in np.linspace(0.,1.,41)]))
sq_trials=[];sq_selected=None;sq_saved={}
for amplitude in [9.,6.,0.,12.]:
    fc_amplitude=amplitude;rows=[];saved={}
    # Exact endpoint identity prevents solving the sweep by moving an
    # interface, stretching a wire or silently changing its resting shape.
    end=fc_curve(1.)[0];core,tails,meta=bl_curves(2.,0.)
    assert np.linalg.norm(end[-1]-tails[0][0])<1e-8
    for t in sq_order:
        p,u,error=fc_curve(t);hit=fc_test(t,t)
        packing,sm=ap_pack(p,error) if hit is None else ({'status':'NOT_TESTED'},[])
        row={'fraction':t,'main_and_tail_controls':sq_controls(t),'solids_failure':hit,'wire_packing':packing,
            'status':'PASS' if hit is None and packing['status']=='PASS' else 'BLOCKED'}
        rows.append(row)
        print('SEQUENTIAL_SCREEN',amplitude,t,row['status'],hit,packing.get('checks',[None])[-1],flush=True)
        if row['status']!='PASS':break
        for slot in range(4):saved[f'f{t:.6f}_slot{slot}']=p+[xx[slot]-xx[0],0.,0.]
    good=len(rows)==len(sq_order) and all(r['status']=='PASS' for r in rows)
    sq_trials.append({'amplitude_mm':amplitude,'status':'PASS' if good else 'BLOCKED','rows':rows})
    if good:sq_selected=amplitude;sq_saved=saved;break
if sq_saved:np.savez_compressed(SQ_OUT/'curves.npz',**sq_saved)
report={'status':'PASS' if sq_selected is not None else 'BLOCKED',
    'scope':'Finite sequential-tail-then-main bend positions against stage solids and upstream conductors',
    'source_main_sha256':source_hash,'script_sha256':sha(SQ_SCRIPT),'helper_sha256':sha(SQ_HELPER),
    'source_failed_packing_sha256':sha(L2_OUT/'packing_screen.json'),
    'selected_amplitude_mm':sq_selected,'planned_fractions':sq_order,'trials':sq_trials,
    'curves_sha256':sha(SQ_OUT/'curves.npz') if sq_saved else None,
    'final_plug_lift_mm':2.,'controls':'upper=max(0,2t-1); lower=min(1,2t); extra vertical straight=A*sin(pi*upper)',
    'constant_length':'PASS_ANALYTICAL_FIXED_MATERIAL_COORDINATE','wire_and_contact_to_structure_margin_mm':.3,
    'continuous_motion':'NOT_TESTED','prior_simultaneous_turn_bound_applicable':False,
    'contact_handling_margin':'BLOCKED','terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-sq_started}
(SQ_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('SEQUENTIAL_BENDS_DONE',report['status'],sq_selected,flush=True)
