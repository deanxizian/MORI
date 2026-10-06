"""Complete the remaining rear-left transition with tangent circular S bends.

Independent prescribed geometry only. Inherit three checked route pools,
keep the source solids and electrical mapping unchanged, and test the new
fixed-yaw wire against every original prefix and moving CAM-side loop.
"""
from pathlib import Path
ANALYTIC_SCRIPT=Path(__file__).resolve();ANALYTIC_ROOT=ANALYTIC_SCRIPT.parent
ANALYTIC_HELPER=ANALYTIC_ROOT/'plan_cam_yaw_fan_v4.py';__file__=str(ANALYTIC_HELPER)
exec(compile(ANALYTIC_HELPER.read_text().split('\nrng=np.random.default_rng',1)[0],str(ANALYTIC_HELPER),'exec'),globals())
__file__=str(ANALYTIC_SCRIPT)
OUT=ANALYTIC_ROOT/'cam_fan_in/final_transition';OUT.mkdir(exist_ok=True)
previous=ANALYTIC_ROOT/'cam_fan_in/fan_in_v4'
previous_report=json.loads((previous/'pool.json').read_text())
previous_arrays=np.load(previous/'curves.npz')
stored={k:previous_arrays[k] for k in previous_arrays.files if not k.startswith('pin1_')}

def s_bend(start,axis,delta,r):
    alpha=math.acos(1-delta/(2*r));n=max(1,math.ceil(r*alpha/.02))
    a=np.linspace(0,alpha,n+1)
    first=start+r*(1-np.cos(a))[:,None]*axis+r*np.sin(a)[:,None]*up
    a=np.linspace(alpha,0,n+1)
    second=first[-1]+r*(np.cos(a)-math.cos(alpha))[:,None]*axis+r*(math.sin(alpha)-np.sin(a))[:,None]*up
    return np.vstack([first,second[1:]]),2*r*alpha,r*(1-math.cos(alpha/(2*n)))

a=body['pin1_yaw0'][-1];b=anchor_points[0]
counts=Counter();examples={};selected=[];started=time.time()
for rise,rx,ry in itertools.product([0.,.5,1.,1.5,2.],[7.2,7.5,8.,9.,10.],[7.2,7.5,8.,9.,10.]):
    counts['tried']+=1
    p0=a+rise*up
    px,lx,ex=s_bend(p0,np.array([1.,0.,0.]),b[0]-a[0],rx)
    py,ly,ey=s_bend(px[-1],np.array([0.,1.,0.]),b[1]-a[1],ry)
    if py[-1,2]>=b[2]:counts['height']+=1;continue
    points=np.vstack([line_points(a,p0)[:-1],px[:-1],py[:-1],line_points(py[-1],b)])
    error=max(ex,ey);sample=fine(points,step=.02)
    hit=self_check(sample,error)
    if hit['status']!='PASS':counts['self']+=1;continue
    hit=local_connections(sample,error,1)
    if hit['status']!='PASS':counts[hit['type']]+=1;examples.setdefault(hit['type'],hit);continue
    hit=fixed_yaw_source(points,error)
    if hit:counts[hit['obstacle']]+=1;examples.setdefault(hit['obstacle'],hit);continue
    idx=len(selected);stored[f'pin1_candidate{idx}']=points
    selected.append({'pin':1,'slot':0,'curve_kind':'two circular S bends and tangent lines',
        'parameters':{'initial_rise_mm':rise,'x_radius_mm':rx,'y_radius_mm':ry},
        'start_mm':a.tolist(),'end_mm':b.tolist(),'x_bend_end_mm':px[-1].tolist(),'y_bend_end_mm':py[-1].tolist(),
        'length_mm':rise+lx+ly+b[2]-py[-1,2],'curve_error_bound_mm':error,
        'minimum_analytic_radius_mm':min(rx,ry),'controls_mm':[],
        'connection_checks':local_connections(sample,error,1)})
    print('ANALYTIC_FAN_FOUND',idx,selected[-1]['parameters'],selected[-1]['length_mm'],flush=True)
    if len(selected)>=3:break
rows=[{'pin':1,'status':'PASS' if selected else 'BLOCKED','counts':dict(counts),'examples':examples,'candidates':selected}]+previous_report['rows'][1:]
np.savez_compressed(OUT/'curves.npz',**stored)
result={**previous_report,'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'BLOCKED',
    'script_sha256':sha(ANALYTIC_SCRIPT),'source_helper_sha256':sha(ANALYTIC_HELPER),
    'source_previous_pool_sha256':sha(previous/'pool.json'),'source_previous_curves_sha256':sha(previous/'curves.npz'),
    'curves_sha256':sha(OUT/'curves.npz'),'rows':rows,'elapsed_s':time.time()-started,
    'scope':'Four individual fixed-yaw transition pools, each versus all moving CAM loops, body prefixes and source solids; mutual transition packing still pending',
    'source_curve_family':'Pin1 circular S bends; pins2/3 cubic Bezier; pin4 cubic plus circular elbow',
    'main_applied':False,'manufacturing_release':False}
(OUT/'pool.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('ANALYTIC_FAN_DONE',result['status'],dict(counts),flush=True)
