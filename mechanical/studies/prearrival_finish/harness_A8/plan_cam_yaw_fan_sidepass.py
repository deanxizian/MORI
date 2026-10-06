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
OUT=ANALYTIC_ROOT/'cam_fan_in/sidepass_transition';OUT.mkdir(exist_ok=True)
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
for side_x,side_y,cross_z in itertools.product([-10.8,-10.9,-11.],[-8.,-8.5,-9.],[209.,210.,211.]):
    counts['tried']+=1;rx=ry=7.2;rise=0.
    side=np.array([side_x,side_y,a[2]])
    delta=side-a;delta[2]=0.;dist=float(np.linalg.norm(delta));axis=delta/dist
    first,l0,e0=s_bend(a,axis,dist,7.2)
    cross=first[-1].copy();cross[2]=cross_z
    if first[-1,2]>cross_z:continue
    px,lx,ex=s_bend(cross,np.array([1.,0.,0.]),b[0]-side_x,7.2)
    py,ly,ey=s_bend(px[-1],np.array([0.,1.,0.]),b[1]-side_y,7.2)
    if py[-1,2]>=b[2]:counts['height']+=1;continue
    points=np.vstack([first[:-1],line_points(first[-1],cross)[:-1],px[:-1],py[:-1],line_points(py[-1],b)])
    error=max(e0,ex,ey);sample=fine(points,step=.02)
    hit=self_check(sample,error)
    if hit['status']!='PASS':counts['self']+=1;continue
    hit=local_connections(sample,error,1)
    if hit['status']!='PASS':counts[hit['type']]+=1;examples.setdefault(hit['type'],hit);continue
    hit=fixed_yaw_source(points,error)
    if hit:counts[hit['obstacle']]+=1;examples.setdefault(hit['obstacle'],hit);continue
    idx=len(selected);stored[f'pin1_candidate{idx}']=points
    selected.append({'pin':1,'slot':0,'curve_kind':'three circular S bends and tangent lines, side passage around the CAM tail',
        'parameters':{'side_x_mm':side_x,'side_y_mm':side_y,'cross_z_mm':cross_z,'radii_mm':[7.2,7.2,7.2]},
        'start_mm':a.tolist(),'end_mm':b.tolist(),'first_bend_end_mm':first[-1].tolist(),'cross_bend_start_mm':cross.tolist(),'x_bend_end_mm':px[-1].tolist(),'y_bend_end_mm':py[-1].tolist(),
        'length_mm':l0+cross_z-first[-1,2]+lx+ly+b[2]-py[-1,2],'curve_error_bound_mm':error,
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
