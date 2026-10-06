"""Constant-length parallel loops whose free column follows the pitch end.

The lower terminal straight has fixed length; its circle/column follows the
moving endpoint. The upper semicircle changes radius, and its height solves
the exact constant-length condition. All curves stay in separate X planes.
"""
from pathlib import Path
FOLLOW_SCRIPT=Path(__file__).resolve();FOLLOW_ROOT=FOLLOW_SCRIPT.parent
FOLLOW_HELPER=FOLLOW_ROOT/'plan_cam_parallel_arcs.py';__file__=str(FOLLOW_HELPER)
exec(compile(FOLLOW_HELPER.read_text().split('\ncounts=Counter();',1)[0],str(FOLLOW_HELPER),'exec'),globals())
__file__=str(FOLLOW_SCRIPT)
OUT=FOLLOW_ROOT/'cam_parallel_pitch/following_arc';OUT.mkdir(exist_ok=True)

def following(ay,az,rb,end_length,pitch,target=None):
    angle=math.radians(pitch);mat=np.asarray(rigidtr(0,pitch))
    b=tails[0][-1]@mat[:3,:3].T+mat[:3,3];b[0]=xc
    column=b[1]+end_length*math.cos(angle)+rb*(1-math.sin(angle));rt=(column-ay)/2
    if rt<REQUIRED_R+.1:return None
    zturn=b[2]+end_length*math.sin(angle)+rb*math.cos(angle)
    base=math.pi*rt+(az-zturn)+rb*(math.pi/2-angle)+end_length
    if target is None:return base,base+2*max(5.,zturn-az+.5)
    height=(target-base)/2
    if height<5.-1e-6 or az+height<zturn+.49999:return None
    a=np.array([xc,ay,az]);top=a+[0.,0.,height];endtop=np.array([xc,column,az+height])
    t=np.linspace(math.pi,0,max(1,math.ceil(math.pi*rt/.02))+1)
    upper=np.c_[np.full_like(t,xc),ay+rt+rt*np.cos(t),az+height+rt*np.sin(t)]
    tt=np.linspace(0.,-math.pi/2+angle,max(1,math.ceil(rb*(math.pi/2-angle)/.02))+1)
    lower=np.c_[np.full_like(tt,xc),column-rb+rb*np.cos(tt),zturn+rb*np.sin(tt)]
    points=np.vstack([line_points(a,top)[:-1],upper[:-1],line_points(endtop,lower[0])[:-1],lower[:-1],line_points(lower[-1],b)])
    error=max(rt,rb)*(1-math.cos(.02/(2*min(rt,rb))))
    return points,{'pitch_deg':pitch,'column_y_mm':column,'upper_arc_lift_mm':height,'top_radius_mm':rt,
        'lower_radius_mm':rb,'bottom_straight_mm':end_length,'vertical_span_mm':az+height-zturn,
        'exact_length_mm':base+2*height,'curve_error_bound_mm':error}

counts=Counter();failures=Counter();examples={};selected=[];stored={};started=time.time()
order=[0,-20,25,-15,20,-10,15,-5,10,5]
for ay,az,rb,end_length in itertools.product([0.,-1.,-2.,1.],[205.,208.,212.],[7.5,8.],[.5,1.,2.]):
    counts['tried']+=1
    bases=[following(ay,az,rb,end_length,p) for p in order]
    if any(b is None for b in bases):counts['radius_rejected']+=1;continue
    target=max(b[1] for b in bases)+.02;rows=[];curves={};reason=None
    for pitch in order:
        q=following(ay,az,rb,end_length,pitch,target)
        if q is None:reason='height_range';break
        points,row=q
        for slot,x in enumerate(xx):
            translated=points+[x-xc,0.,0.]
            hit=check_curve(translated,row['curve_error_bound_mm'],pitch,True)
            if hit:reason=hit['obstacle'];examples.setdefault(reason,{'slot':slot,'params':[ay,az,rb,end_length],**hit});break
            curves[slot,pitch]=translated
        if reason:break
        rows.append(row)
    if reason:
        failures[reason]+=1
        if counts['tried']<=6 or counts['tried']%10==0:print('FOLLOW_REJECT',counts['tried'],reason,examples[reason] if reason in examples else None,flush=True)
        continue
    idx=len(selected)
    for (slot,pitch),points in curves.items():stored[f'candidate{idx}_slot{slot}_pitch{pitch}']=points
    record={'parameters':{'anchor_y_mm':ay,'anchor_z_mm':az,'lower_radius_mm':rb,'terminal_straight_mm':end_length},
        'anchor_slots_mm':[[float(x),ay,az] for x in xx],'exact_length_mm':target,'poses':sorted(rows,key=lambda r:r['pitch_deg'])}
    selected.append(record);print('FOLLOW_FOUND',idx,record['parameters'],target,round(time.time()-started,1),flush=True)
    if len(selected)>=3:break
np.savez_compressed(OUT/'curves.npz',**stored)
result={'status':'PASS' if selected else 'BLOCKED','scope':'Parallel analytic service-loop source clearance at finite poses only',
    'source_main_sha256':source_hash,'script_sha256':sha(FOLLOW_SCRIPT),'helper_sha256':sha(FOLLOW_HELPER),
    'tail_report_sha256':sha(FOLLOW_ROOT/'cam_parallel_pitch/shifted_tail_screen.json'),
    'tail_curves_sha256':sha(FOLLOW_ROOT/'cam_parallel_pitch/shifted_tails.npz'),'curves_sha256':sha(OUT/'curves.npz'),
    'counts':dict(counts),'failures':dict(failures),'examples':examples,'selected':selected,
    'wire_OD_mm':OD,'minimum_radius_required_mm':REQUIRED_R,'surface_gap_required_mm':.3,
    'interplane_surface_gap_mm':float(np.diff(xx).min())-OD,'joint_angle_samples':130,
    'whole_partial_wire_self_and_mutual':'NOT_TESTED','body_prefix_coexistence':'NOT_TESTED',
    'fan_in':'NOT_TESTED','anchors':'NOT_TESTED','continuous_joint_motion':'NOT_TESTED','physical_wire_behavior':'NOT_TESTED',
    'whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
(OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FOLLOW_DONE',result['status'],dict(counts),dict(failures),flush=True)
