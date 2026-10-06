"""Plan four coherent pitch leads in parallel YZ planes.

These are individual wires, not a new ribbon-cable selection. One common
centerline law gives equal constant lengths and an exact inter-plane spacing
bound. Fixed-yaw fan-in from the four original exit phases is separate work.
"""
from pathlib import Path
PAR_SCRIPT=Path(__file__).resolve();PAR_DIR=PAR_SCRIPT.parent
PAR_HELPER=PAR_DIR/'plan_cam_pitch_flex.py';__file__=str(PAR_HELPER)
exec(compile(PAR_HELPER.read_text().split('\nall_rows=[];saved={}',1)[0],str(PAR_HELPER),'exec'),globals())
__file__=str(PAR_SCRIPT);OUT=PAR_DIR/'cam_parallel_pitch';OUT.mkdir(exist_ok=True)
from mathutils.kdtree import KDTree
rng=np.random.default_rng(20261004);started=time.time()
tails,rads,tail_lengths,tail_errors=make_case('forward',11.,20.)
tail_hit=check_paths(tails,tail_errors,True)
tail_bound=pair_gap(tails,tail_errors)
assert tail_hit is None,tail_hit
assert tail_bound>=.3,tail_bound
np.savez_compressed(OUT/'pitch_fixed_tails.npz',**{f'slot{i}':p for i,p in enumerate(tails)})
xvalues=np.array([p[-1,0] for p in tails]);xc=float(xvalues.mean())
endpoint_tangent=np.array([0.,-1.,0.])
def self_hit(points,error):
    finep=np.vstack([np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/.03))+1)[:-1] for a,b in zip(points,points[1:])]+[points[-1:]])
    dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(finep,axis=0),axis=1))];tree=KDTree(len(finep))
    for i,p in enumerate(finep):tree.insert(Vector(p),i)
    tree.balance();threshold=OD+.3+.03+2*error+1e-4
    for i,p in enumerate(finep):
        for _,j,d in tree.find_range(Vector(p),threshold):
            if abs(dist[j]-dist[i])>2.:return {'indices':[i,j],'distance_mm':float(d),'required_mm':threshold}
    return None
def check_four(cs,pitch,full):
    for slot,x in enumerate(xvalues):
        moved=[c+np.array([x-xc,0.,0.]) for c in cs]
        hit=geom_check(moved,pitch,full)
        if hit:return {'slot':slot,**hit}
    return None
counts=Counter();failures=Counter();examples={};selected=[];saved={}
for trial in range(45000):
    counts['tried']+=1
    a=np.array([xc,rng.uniform(8.,13.),rng.uniform(232.,241.)])
    b=tails[0][-1].copy();b[0]=xc
    phi=rng.uniform(-.65,.65)
    params={'mid':[xc,rng.uniform(21.,29.),rng.uniform(217.,242.)],
        'tangent':[0.,math.sin(phi),-math.cos(phi)],'handles':rng.uniform(3.,12.,4).tolist()}
    cs=make(a,b,endpoint_tangent,params)
    if min(min_radius(c,np.linspace(0,1,81)) for c in cs)<REQUIRED_R+.15:counts['curvature']+=1;continue
    hit=check_four(cs,0,False)
    if hit:counts['zero_geometry']+=1;failures[hit['obstacle']]+=1;examples.setdefault(hit['obstacle'],hit);continue
    pitch_data={};lowers=[];uppers=[]
    for pitch in range(-20,26,5):
        mat=np.asarray(rigidtr(0,pitch));bp=b@mat[:3,:3].T+mat[:3,3];tb=endpoint_tangent@mat[:3,:3].T
        ll=[sum(curve_length(c) for c in make(a,bp,tb,params,d)) for d in [0.,15.]]
        if ll[1]<=ll[0]:break
        pitch_data[pitch]=(bp,tb);lowers.append(ll[0]);uppers.append(ll[1])
    if len(pitch_data)!=10 or max(lowers)+.1>min(uppers):counts['length_range']+=1;continue
    target=max(lowers)+.1;poses=[];reason=None
    for pitch,(bp,tb) in pitch_data.items():
        low,high=0.,15.
        for _ in range(33):
            delta=(low+high)/2;cs=make(a,bp,tb,params,delta)
            if sum(curve_length(c) for c in cs)<target:low=delta
            else:high=delta
        delta=(low+high)/2;cs=make(a,bp,tb,params,delta)
        rad=min(min_radius(c,np.linspace(0,1,513)) for c in cs)
        if rad<REQUIRED_R+.05:reason='motion_curvature';break
        hit=check_four(cs,pitch,True)
        if hit:reason=hit['obstacle'];examples.setdefault(reason,hit);break
        p,error=sampled(cs,400);mat=np.asarray(rigidtr(0,pitch))
        end=tails[0]@mat[:3,:3].T+mat[:3,3];end[:,0]=xc
        combined=np.vstack([p,end[-2::-1]])
        hit=self_hit(combined,max(error,max(tail_errors)))
        if hit:reason='self_clearance';examples.setdefault(reason,{'pitch_deg':pitch,**hit});break
        poses.append({'pitch_deg':pitch,'height_adjustment_mm':delta,'controls_mm':[c.tolist() for c in cs],
            'length_mm':sum(curve_length(c) for c in cs),'minimum_sampled_radius_mm':rad,'chord_error_bound_mm':error})
    if reason:counts[reason]+=1;continue
    record={'trial':trial,'anchor_center_mm':a.tolist(),'anchor_slots_mm':[[float(x),float(a[1]),float(a[2])] for x in xvalues],
        'parameters':params,'constant_flex_length_mm':target,'poses':poses}
    index=len(selected);selected.append(record)
    for p in poses:
        points,error=sampled([np.array(c) for c in p['controls_mm']],400)
        for slot,x in enumerate(xvalues):saved[f'candidate{index}_slot{slot}_pitch{p["pitch_deg"]}']=points+np.array([x-xc,0.,0.])
    print('PARALLEL_PITCH_FOUND',len(selected),a.tolist(),target,round(time.time()-started,1),flush=True)
    if len(selected)>=6:break
np.savez_compressed(OUT/'flex_curves.npz',**saved)
result={'status':'PASS' if selected else 'BLOCKED','scope':'Parallel-plane pitch service routes and CAM fixed tails only; fixed yaw fan-in and anchors are absent',
    'source_script_sha256':sha(PAR_SCRIPT),'source_helper_sha256':sha(PAR_HELPER),'source_main_sha256':source_hash,
    'source_candidate_sha256':sha(candidate/'candidate.blend'),'wire_OD_mm':OD,'required_radius_mm':REQUIRED_R,
    'required_surface_gap_mm':.3,'tail_radius_mm':11.,'tail_extension_mm':20.,'tail_lengths_mm':tail_lengths,
    'tail_error_bounds_mm':tail_errors,'tail_source_pose_checks':'PASS','tail_mutual_gap_bound_mm':tail_bound,
    'plane_x_coordinates_mm':xvalues.tolist(),'plane_min_spacing_mm':float(np.min(np.diff(xvalues))),
    'interwire_plane_gap_bound_mm':float(np.min(np.diff(xvalues)))-OD-1e-5,
    'interwire_proof':'Every centerline remains in one distinct constant-X plane in the yaw frame. Pitch rotation is about X; common yaw preserves Euclidean distance. Separation is at least abs(deltaX) everywhere.',
    'counts':dict(counts),'failures':dict(failures),'examples':examples,'selected':selected,
    'fixed_tails_sha256':sha(OUT/'pitch_fixed_tails.npz'),'curves_sha256':sha(OUT/'flex_curves.npz'),
    'anchor_design':'NOT_TESTED','fan_in_from_original_yaw_exits':'NOT_TESTED','continuous_joint_motion':'NOT_TESTED',
    'physical_wire_behavior':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
(OUT/'route_pools.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PARALLEL_PITCH_DONE',result['status'],dict(counts),flush=True)
