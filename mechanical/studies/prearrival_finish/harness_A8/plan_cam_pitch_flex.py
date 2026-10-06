"""Bounded, reproducible search for constant-length yaw/pitch wire continuations.

Only an independent geometric study. Each candidate joins actual stored
partial curves. Neither connector pin order nor physical anchors are inferred.
"""
from pathlib import Path
FLEX_SCRIPT=Path(__file__).resolve(); FLEX_DIR=FLEX_SCRIPT.parent
FLEX_HELPER=FLEX_DIR/'plan_cam_uart_departure.py'
__file__=str(FLEX_HELPER)
exec(compile(FLEX_HELPER.read_text().split('\ntrials=[];selected=[];stored={}',1)[0],str(FLEX_HELPER),'exec'),globals())
__file__=str(FLEX_SCRIPT)
OUT=FLEX_DIR/'cam_pitch_flex';OUT.mkdir(exist_ok=True)
from collections import Counter
body_curves=np.load(FLEX_DIR/'cam_pitch_port/lower_staging/body_partial_curves.npz')
head_curves=np.load(FLEX_DIR/'cam_pitch_port/departure_curves.npz')
center=np.array([0.,0.,float(D['head_z'])]);up=np.array([0.,0.,1.])
family='forward';endpoint_tangent=np.array([0.,-1.,0.])
rng=np.random.default_rng(20261003)
gl_nodes,gl_weights=np.polynomial.legendre.leggauss(64)

def basis(n,t):
    return np.array([math.comb(n,i)*(1-t)**(n-i)*t**i for i in range(n+1)]).T
def evaluate(c,t):
    return basis(5,t)@c
def derivatives(c,t):
    return basis(4,t)@(5*np.diff(c,axis=0)),basis(3,t)@(20*np.diff(c,n=2,axis=0))
def curve_length(c):
    v,_=derivatives(c,(gl_nodes+1)/2)
    return float(np.dot(gl_weights,np.linalg.norm(v,axis=1))/2)
def min_radius(c,t):
    v,a=derivatives(c,t);s=np.linalg.norm(v,axis=1);cross=np.linalg.norm(np.cross(v,a),axis=1)
    if s.min()<1e-7:return 0.
    return float(np.min(np.divide(s**3,cross,out=np.full_like(s,np.inf),where=cross>1e-12)))
def controls(a,b,ta,tb,ha,hb):
    # Collinear first/last three controls make zero end curvature. Adjacent
    # segments share a tangent and have no corner at their common waypoint.
    return np.array([a,a+ha*ta,a+2*ha*ta,b-2*hb*tb,b-hb*tb,b])
def make(a,b,tb,params,delta=0.):
    mid=np.array(params['mid']);mid[2]+=delta
    tangent=np.array(params['tangent']);h=params['handles']
    return [controls(a,mid,up,tangent,h[0],h[1]),controls(mid,b,tangent,tb,h[2],h[3])]
def sampled(cs,n=160):
    p=np.vstack([evaluate(c,np.linspace(0,1,n+1))[:-1] for c in cs]+[cs[-1][-1:]])
    # Convex-hull bound on the second derivative, valid for all t in each span.
    error=max(float(np.linalg.norm(20*np.diff(c,n=2,axis=0),axis=1).max()) for c in cs)/(8*n*n)
    return p,error
def geom_check(cs,pitch,full_yaw=False):
    pts,err=sampled(cs)
    for name,group,m,lo,hi,tree in ob:
        yaws=list(range(-60,61,10)) if full_yaw and group=='body' else [0]
        for yaw in yaws:
            if group=='pitch':
                mat=np.linalg.inv(np.asarray(rigidtr(0,pitch)))
                p=pts@mat[:3,:3].T+mat[:3,3]
            elif group=='yaw':p=pts
            else:
                mat=np.asarray(rigidtr(yaw,0));p=pts@mat[:3,:3].T+mat[:3,3]
            hit=check_one(p,err,lo,hi,m,tree)
            if hit:return {'obstacle':name,'yaw_deg':yaw,'pitch_deg':pitch,**hit}
    return None

all_rows=[];saved={};t0=time.time()
for pin in range(1,5):
    # This is a geometric slot assignment only, never a manufacturing pin map.
    slot=pin-1;a=body_curves[f'pin{pin}_yaw0'][-1];b=head_curves[f'{family}_slot{slot}'][-1]
    counts=Counter();pool=[];failures=Counter();examples={}
    for trial in range(16000):
        counts['tried']+=1
        mid=np.array([rng.uniform(-28,28),rng.uniform(-28,28),rng.uniform(217,255)])
        tangent=b-a;tangent[2]=rng.uniform(-12,12);tangent+=rng.normal(0,8,3)
        tangent/=np.linalg.norm(tangent)
        params={'mid':mid.tolist(),'tangent':tangent.tolist(),'handles':rng.uniform(3,14,4).tolist()}
        cs=make(a,b,endpoint_tangent,params)
        if min(min_radius(c,np.linspace(0,1,65)) for c in cs)<REQUIRED_R+.12:
            counts['curvature_rejected']+=1;continue
        counts['curvature_accepted']+=1
        hit=geom_check(cs,0)
        if hit:
            counts['zero_pose_rejected']+=1;failures[hit['obstacle']]+=1
            examples.setdefault(hit['obstacle'],hit);continue
        counts['zero_pose_accepted']+=1
        # One constant arclength for all pitch poses. Vary only the middle
        # waypoint height; bracket each solution inside a bounded15mm range.
        pitch_data={};lower=[];upper=[]
        for pitch in range(-20,26,5):
            mat=np.asarray(rigidtr(0,pitch));bp=b@mat[:3,:3].T+mat[:3,3];tb=endpoint_tangent@mat[:3,:3].T
            ls=[sum(curve_length(c) for c in make(a,bp,tb,params,d)) for d in [0.,15.]]
            if ls[1]<=ls[0]:break
            pitch_data[pitch]=(bp,tb);lower.append(ls[0]);upper.append(ls[1])
        if len(pitch_data)!=10 or max(lower)>min(upper):counts['length_bracket_rejected']+=1;continue
        target=max(lower)+.1
        if target>min(upper):counts['length_bracket_rejected']+=1;continue
        current=[];reason=None
        for pitch,(bp,tb) in pitch_data.items():
            low,high=0.,15.
            for _ in range(35):
                d=(low+high)/2;curves=make(a,bp,tb,params,d)
                if sum(curve_length(c) for c in curves)<target:low=d
                else:high=d
            d=(low+high)/2;curves=make(a,bp,tb,params,d)
            radius=min(min_radius(c,np.linspace(0,1,513)) for c in curves)
            if radius<REQUIRED_R+.04:reason={'type':'motion_curvature','pitch_deg':pitch,'radius':radius};break
            hit=geom_check(curves,pitch,True)
            if hit:reason={'type':'motion_clearance',**hit};break
            pts,error=sampled(curves,400)
            current.append({'pitch_deg':pitch,'height_adjustment_mm':d,'controls_mm':[c.tolist() for c in curves],
                'length_mm':sum(curve_length(c) for c in curves),'minimum_sampled_radius_mm':radius,'chord_error_bound_mm':error})
        if reason:
            counts[reason['type']+'_rejected']+=1;failures[reason.get('obstacle',reason['type'])]+=1
            examples.setdefault(reason.get('obstacle',reason['type']),reason);continue
        counts['constant_length_motion_accepted']+=1
        record={'pin':pin,'geometric_slot':slot,'trial':trial,'parameters':params,'constant_length_mm':target,'poses':current}
        pool.append(record)
        for row in current:
            cs2=[np.array(c) for c in row['controls_mm']];pts,err=sampled(cs2,400)
            saved[f'pin{pin}_candidate{len(pool)-1}_pitch{row["pitch_deg"]}']=pts
        print('PITCH_FLEX_FOUND',pin,len(pool),round(target,3),round(time.time()-t0,1),flush=True)
        if len(pool)>=6:break
    all_rows.append({'pin':pin,'slot_index':slot,'status':'PASS' if pool else 'BLOCKED','counts':dict(counts),
        'failures':dict(failures),'examples':examples,'candidates':pool})
    print('PITCH_FLEX_PIN',pin,len(pool),dict(counts),round(time.time()-t0,1),flush=True)

np.savez_compressed(OUT/'flex_candidates.npz',**saved)
result={'status':'PASS' if all(r['candidates'] for r in all_rows) else 'BLOCKED',
    'scope':'Individual constant-length pitch continuation pools, fixed geometric slot mapping; not simultaneous full harness',
    'source_script_sha256':sha(FLEX_SCRIPT),'source_helper_sha256':sha(FLEX_HELPER),
    'source_main_sha256':source_hash,'source_candidate_sha256':sha(candidate/'candidate.blend'),
    'body_partial_sha256':sha(FLEX_DIR/'cam_pitch_port/lower_staging/body_partial_curves.npz'),
    'head_partial_sha256':sha(FLEX_DIR/'cam_pitch_port/departure_curves.npz'),
    'curves_sha256':sha(OUT/'flex_candidates.npz'),'seed':20261003,'rows':all_rows,
    'required_radius_mm':REQUIRED_R,'wire_OD_mm':OD,'required_surface_gap_mm':.3,
    'physical_pin_map':'BLOCKED','wire_self_and_mutual_contacts':'NOT_TESTED','prefix_continuation_contacts':'NOT_TESTED',
    'continuous_motion':'NOT_TESTED','anchors':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,
    'manufacturing_release':False,'elapsed_s':time.time()-t0}
(OUT/'flex_pool.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('PITCH_FLEX_POOL_DONE',result['status'],flush=True)
