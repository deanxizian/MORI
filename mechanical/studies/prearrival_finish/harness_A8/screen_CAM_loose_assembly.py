"""Constant-length lateral reshaping during CAM/cradle installation.

No hardware/anchor changes: free wire spans may change shape while the CAM
module is raised. Preserve end straights, material length, clearance and bend
radius. This is a prescribed kinematic family, not a passive wire simulation.
"""
from pathlib import Path
LA_SCRIPT=Path(__file__).resolve();LA_ROOT=LA_SCRIPT.parent
LA_HELPER=LA_ROOT/'check_CAM_wired_cradle_insertion.py';__file__=str(LA_HELPER)
exec(compile(LA_HELPER.read_text().split('\nwi_rows=[];',1)[0],str(LA_HELPER),'exec'),globals())
__file__=str(LA_SCRIPT);LA_OUT=LA_ROOT/'cam_sequence_loose';LA_OUT.mkdir(exist_ok=True)
la_nodes,la_weights=np.polynomial.legendre.leggauss(96)
la_r=7.5;la_tail_planar=5+math.pi*la_r/2+(9.5-slots[0,1]-la_r)
la_tail_span=la_tail_planar-5
def la_integral(fn,a,b):
    p=a+(la_nodes+1)*(b-a)/2
    return float(np.dot(la_weights,fn(p))*(b-a)/2)
def la_tail_length(shift,span):
    fn=lambda s:np.sqrt(1+(shift/span*(30*(s/span)**2-60*(s/span)**3+30*(s/span)**4))**2)
    return float(la_tail_planar-span+la_integral(fn,0.,span))
LA_TOTAL=wi_L+la_tail_length(1.8875,16.)

def la_profile(s,L,w,v=.27,end=3.,first=4.,turn=10.,last=6.):
    speed=v*w;a=(L+5+first/2-last/2-turn-end/v)/2
    assert a>5+first and a+turn<L-last
    s=np.asarray(s);x=np.zeros(s.shape);d=x.copy()
    q=np.clip(s-5,0,first)
    x-=speed/2*(q-first/math.pi*np.sin(math.pi*q/first))
    d-=np.where((s>=5)&(s<=5+first),speed/2*(1-np.cos(math.pi*q/first)),0)
    q=np.clip(s-5-first,0,a-5-first);x-=speed*q
    d-=np.where((s>5+first)&(s<=a),speed,0)
    q=np.clip(s-a,0,turn);x-=speed*turn/math.pi*np.sin(math.pi*q/turn)
    d-=np.where((s>a)&(s<=a+turn),speed*np.cos(math.pi*q/turn),0)
    q=np.clip(s-a-turn,0,L-last-a-turn);x+=speed*q
    d+=np.where((s>a+turn)&(s<=L-last),speed,0)
    q=np.clip(s-L+last,0,last);x+=speed/2*(q+last/math.pi*np.sin(math.pi*q/last))
    d+=np.where(s>L-last,speed/2*(1+np.cos(math.pi*q/last)),0)
    return x,d,{'first':[5,5+first],'turn':[a,a+turn],'last':[L-last,L],
        'first_accel':speed*math.pi/(2*first),'turn_accel':speed*math.pi/turn,'last_accel':speed*math.pi/(2*last)}

def la_core_length(L,w):
    _,_,regions=la_profile(np.array([0.,L]),L,w)
    knots=[0.,5.,regions['first'][1],regions['turn'][0],regions['turn'][1],regions['last'][0],L]
    return sum(la_integral(lambda s:np.sqrt(1+la_profile(s,L,w)[1]**2),a,b) for a,b in zip(knots,knots[1:]))

def la_family(h):
    w=h/42.;shift=1.8875+3*w;span=16+(la_tail_span-16)*w
    tail_length=la_tail_length(shift,span);target=LA_TOTAL-tail_length
    low=60.;high=80.
    for _ in range(50):
        mid=(low+high)/2
        if la_core_length(mid,w)>target:high=mid
        else:low=mid
    L=(low+high)/2;zturn=wi_zero_turn+h
    base=math.pi*wi_rt+wi_z-zturn+wi_rb*math.pi/2+wi_end
    height=(L-base)/2;lengths=np.array([height,math.pi*wi_rt,wi_z+height-zturn,wi_rb*math.pi/2,wi_end])
    assert min(lengths)>0 and height>=5-1e-8
    bounds=np.r_[0.,np.cumsum(lengths)];_,_,regions=la_profile(np.array([0.,L]),L,w)
    knots=sorted(set(bounds.tolist()+regions['first']+regions['turn']+regions['last']+[4.3]))
    s=np.r_[np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/.025))+1)[:-1] for a,b in zip(knots,knots[1:])]),L]
    p=np.zeros((len(s),3));p[:,0]=xx[0]
    for k in range(5):
        ids=np.flatnonzero((s>=bounds[k]-1e-10)&(s<=bounds[k+1]+1e-10));q=s[ids]-bounds[k]
        if k==0:p[ids,1]=wi_y;p[ids,2]=wi_z+q
        elif k==1:
            th=math.pi-q/wi_rt;p[ids,1]=wi_y+wi_rt+wi_rt*np.cos(th);p[ids,2]=wi_z+height+wi_rt*np.sin(th)
        elif k==2:p[ids,1]=wi_column;p[ids,2]=wi_z+height-q
        elif k==3:
            th=-q/wi_rb;p[ids,1]=wi_column-wi_rb+wi_rb*np.cos(th);p[ids,2]=zturn+wi_rb*np.sin(th)
        else:p[ids,1]=wi_b[1]+wi_end-q;p[ids,2]=wi_b[2]+h
    p[:,0]+=la_profile(s,L,w)[0]
    radius=math.inf;accel=0.;intervals=[]
    for a,b in zip(knots,knots[1:]):
        mid=(a+b)/2;yz=1/wi_rt if bounds[1]<mid<bounds[2] else (1/wi_rb if bounds[3]<mid<bounds[4] else 0.)
        x=max([regions[key+'_accel'] for key in ['first','turn','last'] if regions[key][0]<mid<regions[key][1]] or [0.])
        v=math.hypot(yz,x);accel=max(accel,v)
        if v>0:radius=min(radius,1/v)
        intervals.append({'arc_interval_mm':[a,b],'second_derivative_bound':v})
    error=accel*.025**2/8
    tails_new,tail_errors,_,tail_s,_=shifted_tails(la_r,shift,span-1e-9,9.5)
    tails_new=[q+[0,0,h] for q in tails_new]
    tail_radius=1/math.hypot(1/la_r,(10*math.sqrt(3)/3)*shift/span**2)
    assert np.linalg.norm(p[-1]-tails_new[0][-1])<1e-8
    assert np.max(np.abs(p[s<=5,0]-xx[0]))<1e-8
    return p,tails_new,{'lift_mm':h,'weight':w,'planar_core_length_mm':L,'core_3D_length_mm':la_core_length(L,w),
        'tail_3D_length_mm':tail_length,'total_material_model_mm':la_core_length(L,w)+tail_length,
        'core_curve_error_mm':error,'tail_curve_error_mm':tail_errors[0],
        'core_radius_bound_mm':radius,'tail_radius_bound_mm':tail_radius,
        'core_height_mm':height,'tail_shift_mm':shift,'tail_shift_span_mm':span,
        'core_derivative_intervals':intervals,'core_max_x_slope':.27*w}

la_rows=[];la_curves={};la_start=time.time()
print('LOOSE_BOUNDS',{n:list(ss[n].m.bounding_box()) for n in ['Pitch_Yoke','Yaw_Servo','Pitch_Servo','CAM_Mainboard']},'required_R',REQUIRED_R,flush=True)
for h in [0.,42.,21.,9.,12.,36.,3.,6.,15.,18.,24.,27.,30.,33.,39.]:
    core,tails_new,meta=la_family(h);failure=None;samples={};minimum=math.inf
    if min(meta['core_radius_bound_mm'],meta['tail_radius_bound_mm'])<REQUIRED_R:
        failure={'kind':'radius','required_mm':REQUIRED_R}
    for slot in range(4):
        if failure:break
        c=core+[xx[slot]-xx[0],0,0];t=tails_new[slot]
        la_curves[f'lift{h}_core{slot}']=c;la_curves[f'lift{h}_tail{slot}']=t
        for kind,p,err in [('core',c,meta['core_curve_error_mm']),('tail',t,meta['tail_curve_error_mm'])]:
            failure=wi_source(p,err,h,kind,slot)
            if failure:break
        if failure:break
        joined=np.vstack([c,t[-2::-1]]);sample=fine(joined,.005);err=max(meta['core_curve_error_mm'],meta['tail_curve_error_mm'])
        packing=pw_pack(sample,err,slot,0)
        if packing['status']!='PASS':failure={'kind':'packing','slot':slot,**packing};break
        minimum=min(minimum,packing['minimum_fan_body_gap_bound_mm']);samples[slot]=(sample,err)
    if not failure:
        for a,b in itertools.combinations(range(4),2):
            aa,ea=samples[a];bb,eb=samples[b];r=pair(aa,bb,ea,eb)
            if r['status']!='PASS' and r['gap_bound_mm']>.28:
                aa=fine(aa[0],.001);bb=fine(bb[0],.001);r=pair(aa,bb,ea,eb);r['refined_step_mm']=.001
            minimum=min(minimum,r['gap_bound_mm'])
            if r['status']!='PASS':failure={'kind':'mutual','slots':[a,b],**r};break
    row={'status':'BLOCKED' if failure else 'PASS',**meta,'failure':failure,'minimum_pack_gap_mm':minimum if math.isfinite(minimum) else None}
    la_rows.append(row);print('LOOSE_CASE',h,row['status'],failure,'min_gap',row['minimum_pack_gap_mm'],'seconds',round(time.time()-la_start,1),flush=True)
np.savez_compressed(LA_OUT/'curves.npz',**la_curves)
report={'status':'PASS' if all(r['status']=='PASS' for r in la_rows) else 'BLOCKED',
    'scope':'Prescribed equal-length lateral reshaping at fifteen assembly positions, with fixed source/anchors',
    'source_main_sha256':source_hash,'script_sha256':sha(LA_SCRIPT),'helper_sha256':sha(LA_HELPER),
    'curves_sha256':sha(LA_OUT/'curves.npz'),'source_anchor_sha256':sha(WI_ANCHOR/'Pitch_Cradle.npz'),
    'total_core_tail_length_mm':LA_TOTAL,'rows':la_rows,'main_applied':False,'whole_harness':'BLOCKED',
    'physical_behavior':'NOT_TESTED','continuous_motion':'NOT_TESTED','full_installation':'NOT_TESTED','manufacturing_release':False}
(LA_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('LOOSE_ASSEMBLY_DONE',report['status'],flush=True)
