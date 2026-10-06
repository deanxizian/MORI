"""Yaw-fixed transitions from the original neck exits to a shared CAM loop.

Search only independent wire geometry, with every unchanged source solid and
the already checked moving four-wire loop present. Each candidate must join
its own prefix and loop with upward tangents. Physical mounting is separate.
"""
from pathlib import Path
FAN_SCRIPT=Path(__file__).resolve();FAN_ROOT=FAN_SCRIPT.parent
FAN_HELPER=FAN_ROOT/'plan_cam_following_arc.py';__file__=str(FAN_HELPER)
exec(compile(FAN_HELPER.read_text().split('\ncounts=Counter();',1)[0],str(FAN_HELPER),'exec'),globals())
__file__=str(FAN_SCRIPT)
from mathutils.kdtree import KDTree
PAIR_HELPER=FAN_ROOT/'check_cam_pitch_flex_packing.py'
exec(compile('def fine'+PAIR_HELPER.read_text().split('def fine',1)[1].split('\nbody_samples=',1)[0],str(PAIR_HELPER),'exec'),globals())
OUT=FAN_ROOT/'cam_fan_in/fan_in_v4';OUT.mkdir(exist_ok=True)
upper=FAN_ROOT/'cam_fan_in/short_tail_v2';upper_meta=json.loads((upper/'screen.json').read_text())
upper_pack=json.loads((upper/'packing.json').read_text());assert upper_pack['status']=='PASS'
loop_index=0;assert upper_pack['rows'][loop_index]['status']=='PASS'
chosen=upper_meta['selected'][loop_index];anchor_points=np.array(chosen['anchor_slots_mm'])
tails=[np.load(upper/'tails.npz')[f'slot{i}'] for i in range(4)]
uarrays=np.load(upper/'curves.npz');body=np.load(FAN_ROOT/'cam_pitch_port/lower_staging/body_partial_curves.npz')
body_meta=json.loads((FAN_ROOT/'body_prefix_v2/body_to_yaw_motion.json').read_text());body_error=max(r['curve_error_bound_mm'] for r in body_meta['rows'])
tail_error=tr['selected']['curve_error_bound_mm']
loop_samples={}
for p in chosen['poses']:
    pitch=p['pitch_deg'];mat=np.asarray(rigidtr(0,pitch))
    for slot in range(4):
        core=uarrays[f'candidate{loop_index}_slot{slot}_pitch{pitch}'];tail=tails[slot]@mat[:3,:3].T+mat[:3,3]
        joined=np.vstack([core,tail[-2::-1]])
        loop_samples[slot,pitch]=(fine(joined,step=.01),max(tail_error,p['curve_error_bound_mm']))
reverse_loop_samples={}
for key,(sample,error) in loop_samples.items():
    op,os,ot,ostep=sample
    rt=KDTree(len(op))
    for i,pt in enumerate(op[::-1]):rt.insert(Vector(pt),i)
    rt.balance()
    reverse_loop_samples[key]=(op[::-1],os[-1]-os[::-1],rt,ostep)
body_samples={(pin,yaw):fine(body[f'pin{pin}_yaw{yaw}'],step=.02) for pin in range(1,5) for yaw in range(-60,61,10)}

def evaluate(c,t):
    return basis(3,t)@c
def derivatives(c,t):
    return basis(2,t)@(3*np.diff(c,axis=0)),basis(1,t)@(6*np.diff(c,n=2,axis=0))
def controls(a,b,ta,tb,ha,hb):
    return np.array([a,a+ha*ta,b-hb*tb,b])
# Tangents are continuous; unlike the earlier quintic family, nonzero
# endpoint curvature is allowed, as it is at the accepted circle/line joins.
def sampled_dense(cs):
    points=[];error=0.
    for c in cs:
        n=max(200,math.ceil(float(np.linalg.norm(5*np.diff(c,axis=0),axis=1).max())/.035))
        points.append(evaluate(c,np.linspace(0,1,n+1))[:-1])
        error=max(error,float(np.linalg.norm(20*np.diff(c,n=2,axis=0),axis=1).max())/(8*n*n))
    return np.vstack(points+[cs[-1][-1:]]),error

def quick_rejection(points,pitch):
    # Rejection only: exact curve points already closer than required. Do not
    # use this coarse pass to certify intervening curve spans.
    allowance=OD/2+.3-1e-5
    for name,group,m,lo,hi,tree in ob:
        if group=='pitch':
            mat=np.linalg.inv(np.asarray(rigidtr(0,pitch)));q=points@mat[:3,:3].T+mat[:3,3]
        else:q=points
        indices=np.flatnonzero(np.all(q>=lo-allowance,axis=1)&np.all(q<=hi+allowance,axis=1))
        for i in indices:
            if float(tree.find_nearest(Vector(q[i]))[3])<allowance:return name
    return None

def fixed_yaw_source(points,error):
    for name,group,m,lo,hi,tree in ob:
        angles=range(-20,26,5) if group=='pitch' else (range(-60,61,10) if group=='body' else [0])
        for angle in angles:
            if group=='pitch':mat=np.linalg.inv(np.asarray(rigidtr(0,angle)))
            elif group=='body':mat=np.asarray(rigidtr(angle,0))
            else:mat=np.eye(4)
            q=points@mat[:3,:3].T+mat[:3,3]
            hit=check_one(q,error,lo,hi,m,tree)
            if hit:return {'obstacle':name,'relative_group':group,'angle_deg':angle,**hit}
    return None

def local_connections(sample,error,pin):
    # Own prefix joins the fan start; own loop joins its end. Reverse the fan
    # only for the latter so the same arclength-aware seam checker is used.
    slot=pin-1;p,s,tree,step=sample
    rev=(p[::-1],s[-1]-s[::-1],None,step)
    minimum_loop=math.inf;minimum_body=math.inf
    for pitch in range(-20,26,5):
        own,oe=loop_samples[slot,pitch]
        reverse_loop=reverse_loop_samples[slot,pitch]
        hit=own_prefix_check(rev,reverse_loop,error,oe)
        if hit['status']!='PASS':
            ii,jj=hit['indices'];return {'type':'own_loop','pitch_deg':pitch,'fan_point_mm':rev[0][ii].tolist(),'loop_point_mm':reverse_loop[0][jj].tolist(),**hit}
        for other in range(4):
            if other==slot:continue
            so,eo=loop_samples[other,pitch];hit=pair(sample,so,error,eo);minimum_loop=min(minimum_loop,hit['gap_bound_mm'])
            if hit['status']!='PASS':return {'type':'other_loop','slot':other,'pitch_deg':pitch,**hit}
    for yaw in range(-60,61,10):
        mat=np.asarray(rigidtr(yaw,0));q=p@mat[:3,:3].T+mat[:3,3];qs=(q,s,None,step)
        hit=own_prefix_check(qs,body_samples[pin,yaw],error,body_error)
        if hit['status']!='PASS':return {'type':'own_body_prefix','yaw_deg':yaw,**hit}
        for other in range(1,5):
            if other==pin:continue
            hit=pair(qs,body_samples[other,yaw],error,body_error);minimum_body=min(minimum_body,hit['gap_bound_mm'])
            if hit['status']!='PASS':return {'type':'other_body_prefix','pin':other,'yaw_deg':yaw,**hit}
    return {'status':'PASS','minimum_other_loop_gap_mm':minimum_loop,'minimum_other_prefix_gap_mm':minimum_body}

rng=np.random.default_rng(202610041);rows=[];stored={};started=time.time()
parameter_source=FAN_ROOT/'cam_fan_in/curvature_prefilter_v4/parameters.json'
parameter_rows=json.loads(parameter_source.read_text())['rows']
for pin in range(1,5):
    a=body[f'pin{pin}_yaw0'][-1];b=anchor_points[pin-1];counts=Counter();examples={};selected=[]
    pin_started=time.time()
    choices=parameter_rows[pin-1]['candidates']
    if pin==4:choices=[{'start_handle':float(h),'end_handle':float(k),'elbow_radius':float(r)} for h,k,r in itertools.product(np.linspace(20.,29.,10),np.linspace(8.5,12.,8),[7.2,7.5])]
    for trial,params in enumerate(choices):
        if trial%20==0:
            print('FAN_PROGRESS',pin,trial,dict(counts),round(time.time()-pin_started,2),flush=True)
        if time.time()-pin_started>90:
            counts['stopped_at_time_budget']=1;break
        counts['tried']+=1
        arc_info=None
        if pin==4:
            r=params['elbow_radius'];c0=b+np.array([r,0.,-r])
            cs=[controls(a,c0,up,np.array([-1.,0.,0.]),params['start_handle'],params['end_handle'])]
            arc_info={'radius_mm':r,'start_mm':c0.tolist(),'end_mm':b.tolist(),'angle_rad':math.pi/2,'plane':'XZ, initial tangent -X, final +Z'}
        else:cs=make(a,b,up,params)
        if min(min_radius(c,np.linspace(0,1,101)) for c in cs)<REQUIRED_R+.15:counts['curvature']+=1;continue
        qp,_=sampled(cs,180)
        if arc_info:
            theta=np.linspace(0,math.pi/2,181);arc=c0+np.c_[-r*np.sin(theta),np.zeros_like(theta),r*(1-np.cos(theta))]
            qp=np.vstack([qp,arc[1:]])
        bad=None
        for pitch in [0,-20,25]:
            bad=quick_rejection(qp,pitch)
            if bad:break
        if bad:counts['quick_'+bad]+=1;continue
        points,error=sampled_dense(cs)
        if arc_info:
            count=math.ceil(math.pi*r/2/.02);theta=np.linspace(0,math.pi/2,count+1)
            arc=c0+np.c_[-r*np.sin(theta),np.zeros_like(theta),r*(1-np.cos(theta))]
            points=np.vstack([points,arc[1:]]);error=max(error,r*(1-math.cos(math.pi/(4*count))))
        sample=fine(points,step=.02);hit=self_check(sample,error)
        if hit['status']!='PASS':counts['self']+=1;examples.setdefault('self',hit);continue
        hit=local_connections(sample,error,pin)
        if hit['status']!='PASS':
            kind=hit['type'];counts[kind]+=1
            if kind not in examples:
                examples[kind]={**hit,'controls_mm':[c.tolist() for c in cs],'parameters':params}
                stored[f'pin{pin}_first_{kind}']=points
            continue
        print('FAN_FULL_SOURCE',pin,trial,round(time.time()-started,2),flush=True)
        hit=fixed_yaw_source(points,error)
        if hit:counts[hit['obstacle']]+=1;examples.setdefault(hit['obstacle'],hit);continue
        idx=len(selected);stored[f'pin{pin}_candidate{idx}']=points
        selected.append({'pin':pin,'slot':pin-1,'trial':trial,'controls_mm':[c.tolist() for c in cs],
            'parameters':params,'arc':arc_info,'length_mm':sum(curve_length(c) for c in cs)+(r*math.pi/2 if arc_info else 0.),'curve_error_bound_mm':error,
            'minimum_sampled_radius_mm':min(min_radius(c,np.linspace(0,1,1025)) for c in cs),'connection_checks':hit})
        print('FAN_FOUND',pin,idx,selected[-1]['length_mm'],round(time.time()-started,1),flush=True)
        if len(selected)>=3:break
    rows.append({'pin':pin,'status':'PASS' if selected else 'BLOCKED','counts':dict(counts),'examples':examples,'candidates':selected})
    print('FAN_PIN_DONE',pin,dict(counts),len(selected),round(time.time()-started,1),flush=True)
    np.savez_compressed(OUT/'curves.npz',**stored)
    result={'status':'PASS' if len(rows)==4 and all(r['status']=='PASS' for r in rows) else 'BLOCKED',
        'script_sha256':sha(FAN_SCRIPT),'source_helper_sha256':sha(FAN_HELPER),'source_pair_helper_sha256':sha(PAIR_HELPER),
        'source_main_sha256':source_hash,'source_loop_index':loop_index,'source_loop_screen_sha256':sha(upper/'screen.json'),
        'source_loop_packing_sha256':sha(upper/'packing.json'),'source_loop_curves_sha256':sha(upper/'curves.npz'),
        'source_body_prefix_sha256':sha(FAN_ROOT/'cam_pitch_port/lower_staging/body_partial_curves.npz'),
        'curves_sha256':sha(OUT/'curves.npz'),'rows':rows,'wire_OD_mm':OD,'required_radius_mm':REQUIRED_R,
        'source_tail_sha256':sha(upper/'tails.npz'),'source_parameters_sha256':sha(parameter_source),'budget':'up to 300 curvature-prefiltered trials or 90 seconds per pin; partial family only','curve_degree':3,'scope':'Individual yaw-fixed cubic transitions with every moving CAM loop as obstacle; all four transition mutual packing not yet checked',
        'mutual_fan_in_packing':'NOT_TESTED','anchors':'NOT_TESTED','continuous_collision':'NOT_TESTED',
        'full_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,'elapsed_s':time.time()-started}
    (OUT/'pool.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('FAN_IN_DONE',result['status'],flush=True)
