"""Lift one CAM root bend and smoothly return before the neck entry.

Uses an exact planar arc-length parameter and a quintic height transition.
The circular root elbow and unchanged terminal descent retain R7. Only
planar middle paths of R9 or greater are lifted, with a conservative spatial
curvature bound. Lengths of lifted paths are bounds, never labelled exact.
"""
from pathlib import Path
import sys, json, math, time, collections
HERE=Path(__file__).resolve().parent; PROJECT=HERE.parents[3]
OUT=HERE/'remaining_routes/cam_root_lift'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'mechanical/scripts')); sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from curvature_paths import paths,arc
from curve_clearance import prepared,self_clear
from bounded_curve_checks import pair_threshold
ctx=Context();start=time.time();step=.04;UP=np.array([0.,0.,1.])
pool_dir=HERE/'remaining_routes/higher_cam_stagger'
source=json.loads((pool_dir/'body_prefix_screen.json').read_text());assert source['status']=='PASS'
for name,h in {**source['sources'],**source['inputs']}.items():assert sha(PROJECT/name)==h,name
original=np.load(pool_dir/'body_prefix_candidates.npz');assert sha(pool_dir/'body_prefix_candidates.npz')==source['curve_sha256']
lane_dir=HERE/'remaining_routes/higher_entry'; lane_report=json.loads((lane_dir/'neck_screen.json').read_text())
lane=next(r for r in lane_report['results'] if r['z0_mm']==142.);assert lane['status']=='PASS'
neck=np.load(lane_dir/'neck_candidates.npz');assert sha(lane_dir/'neck_candidates.npz')==lane_report['curve_sha256']
def line(a,b):return np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)
roots={f['endpoint']:prepared(line(np.array(f['p']),np.array(f['p'])+5*UP),f['OD']/2,0.) for f in source['functions']}
local={i:prepared(neck[f'z142.0_wire{i}_y0'],.5842 if i<7 else .3302,lane['chord_error_mm']) for i in range(11)}
def planar_samples(plan,first,last):
    centres=plan['circle_centres_mm'];signs=plan['turn_signs'];R=plan['radius_mm'];t=plan['tangent_points_mm']
    if 'S' in plan['family']:
        a,L0,e0,_=arc(np.array(centres[0]),first,np.array(t[0]),signs[0],R,step)
        b=np.linspace(t[0],t[1],max(2,math.ceil(np.linalg.norm(np.array(t[1])-t[0])/step)+1))
        L1=float(np.linalg.norm(np.array(t[1])-t[0]));e1=0.
        c,L2,e2,_=arc(np.array(centres[1]),np.array(t[1]),last,signs[1],R,step)
    else:
        a,L0,e0,_=arc(np.array(centres[0]),first,np.array(t[0]),signs[0],R,step)
        b,L1,e1,_=arc(np.array(centres[1]),np.array(t[0]),np.array(t[1]),signs[1],R,step)
        c,L2,e2,_=arc(np.array(centres[2]),np.array(t[1]),last,signs[2],R,step)
    ss=np.r_[np.linspace(0,L0,len(a)),np.linspace(L0,L0+L1,len(b))[1:],np.linspace(L0+L1,L0+L1+L2,len(c))[1:]]
    xy=np.vstack([a,b[1:],c[1:]])
    assert abs(ss[-1]-plan['analytic_length_mm'])<1e-7
    return xy,ss,max(e0,e1,e2)

rows=[];curves={};failures=collections.Counter();witness={};trials=0
def failed(hit):
    key=hit.get('object',hit.get('kind','unknown'));failures[key]+=1;witness.setdefault(key,hit)
for old in [r for rs in source['pools'].values() for r in rs if r['planar_radius_mm']>=9]:
    p=original[old['id']];R=old['minimum_centerline_radius_mm'];n=math.ceil(old['lead_mm']/.06)+1
    na=math.ceil(R*math.pi/2/.06)+1;middle_start=n+na-2
    assert abs(p[middle_start,2]-old['plane_z_mm'])<1e-8
    middle_end=middle_start
    while middle_end+1<len(p) and abs(p[middle_end+1,2]-old['plane_z_mm'])<1e-8:middle_end+=1
    first=p[middle_start,:2];last=p[middle_end,:2]
    heading=lambda degree:np.array([math.cos(math.radians(degree)),math.sin(math.radians(degree))])
    candidates=list(paths(first,heading(old['entry_deg']),last,heading(old['exit_deg']),old['planar_radius_mm'],.06))
    plan=next(q for q in candidates if q['family']==old['family'])
    assert plan['points_xy_mm'].shape==p[middle_start:middle_end+1,:2].shape
    assert np.allclose(plan['points_xy_mm'],p[middle_start:middle_end+1,:2],atol=1e-7,rtol=0)
    xy,station,error_plan=planar_samples(plan,first,last)
    near={**{'root_'+k:v for k,v in roots.items() if k!=old['endpoint']},
          **{'neck_'+str(k):v for k,v in local.items() if k!=old['slot']}}
    for delta,plateau,run in [(1.1,0.,16.),(1.1,4.,16.),(1.1,4.,24.),(1.4,0.,20.),(1.4,4.,24.)]:
        if station[-1]<plateau+run+1:continue
        trials+=1;v=np.clip((station-plateau)/run,0,1)
        height=delta*(1-10*v**3+15*v**4-6*v**5)
        middle=np.c_[xy,old['plane_z_mm']+height]
        d1=1.875*delta/run;d2=(10/math.sqrt(3))*delta/run**2
        radius_bound=1/math.sqrt((1+d1*d1)/old['planar_radius_mm']**2+d2*d2)
        assert radius_bound>=7.
        # Each exact planar segment uses arc-length sampling; the extra height
        # sagitta is bounded by max|z''| ds^2/8, added to the planar sagitta.
        error=max(old['chord_error_mm'],error_plan+d2*step**2/8)
        stem=line(p[0],p[n-1]+delta*UP)
        root_arc=p[n-1:middle_start+1]+delta*UP
        end=p[middle_end:]
        assert np.linalg.norm(root_arc[-1]-middle[0])<1e-7
        assert np.linalg.norm(middle[-1]-end[0])<1e-7
        curve=np.vstack([stem,root_arc[1:],middle[1:],end[1:]])
        hit=ctx.clear(stem,radius=old['OD_mm']/2,ignore=['Plug_'+old['port']])
        if not hit:hit=ctx.clear(curve[len(stem)-1:],radius=old['OD_mm']/2,chord_error=error)
        if hit:failed(hit);continue
        item=prepared(curve,old['OD_mm']/2,error)
        for name,other in near.items():
            result=pair_threshold(item,other)
            if result['status']!='PASS':hit=dict(object=name,**result);break
        if hit:failed(hit);continue
        result=self_clear(item)
        if result['status']!='PASS':failed(dict(kind='self',**result));continue
        row={k:v for k,v in old.items() if k not in ['id','analytic_length_mm']}
        row.update(id='lift_'+str(len(rows)),base_id=old['id'],lead_mm=old['lead_mm']+delta,
            lift_mm=delta,plateau_mm=plateau,height_return_length_mm=run,
            length_lower_bound_mm=old['analytic_length_mm']+delta,
            length_upper_bound_mm=old['analytic_length_mm']+delta+5*delta**2/(7*run),
            length_sort_mm=old['analytic_length_mm']+delta+5*delta**2/(7*run),
            planar_base_radius_mm=old['planar_radius_mm'],spatial_middle_radius_lower_bound_mm=radius_bound,
            chord_error_mm=error,length_basis='Spatial arc-length upper/lower bounds; not exact analytic length or supplier cut length')
        rows.append(row);curves[row['id']]=curve
    if len(rows) and len(rows)%20==0:print('ROOT_LIFT_PROGRESS',len(rows),trials,flush=True)
ctx.assert_unchanged();np.savez_compressed(OUT/'body_prefix_candidates.npz',**curves)
report=dict(status='PASS' if rows else 'BLOCKED',scope='Individual root-height alternatives only',sources=ctx.sources,
    inputs={str(p.relative_to(PROJECT)):sha(p) for p in [pool_dir/'body_prefix_screen.json',pool_dir/'body_prefix_candidates.npz',lane_dir/'neck_screen.json',lane_dir/'neck_candidates.npz',HERE.parent/'harness_A8/body_prefix_v2/curvature_paths.py',HERE/'bounded_curve_checks.py']},
    pools={'lifted_CAM':rows},functions=source['functions'],z0_mm=142.,angles_deg=lane['angles_deg'],trials=trials,
    fail_counts=dict(failures),first_witness=witness,curve_sha256=sha(OUT/'body_prefix_candidates.npz'),
    curvature_bound='For unit-speed planar path, conservative sqrt((1+max(z_prime)^2)/R^2+max(z_second)^2). Root/end elbows unchanged R7; height function has zero first/second derivative at joins.',
    length_bound='sqrt(1+z_prime^2) lies between1 and1+z_prime^2/2; quintic derivative-squared integral=10*delta^2/(7*run). Add lifted straight stem delta.',
    full_harness='BLOCKED',main_changed=False,script_sha256=sha(Path(__file__)),elapsed_s=time.time()-start)
(OUT/'body_prefix_screen.json').write_text(json.dumps(report,indent=2)+'\n')
print('ROOT_LIFT_DONE',report['status'],len(rows),report['elapsed_s'],flush=True)
