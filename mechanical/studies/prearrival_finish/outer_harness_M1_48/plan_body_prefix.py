"""Connect native J5 roots to outer R8 neck corridors with tangent R7+ paths."""
from pathlib import Path
import sys,json,math,itertools,time,hashlib
from collections import Counter
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from native_context import *
ctx=Context();started=time.time()
MATH=HERE.parent/'harness_A8/body_prefix_v2/curvature_paths.py'
sys.path.insert(0,str(MATH.parent));from curvature_paths import paths
import inspect
assert Path(inspect.getsourcefile(paths)).resolve()==MATH
neck_file=HERE/'selected_necks.npz'
neck_cache=np.load(neck_file)
neck_report=json.loads((HERE/'selected_necks.json').read_text());assert neck_report['status']=='PASS'
neck_parameters={r['angle_deg']:r for r in neck_report['selected']}
necks={r['angle_deg']:neck_cache[r['curve_key']] for r in neck_report['selected']}
for angle,p in necks.items():
    assert ctx.clear(p,8*(1-math.cos(math.pi/400))) is None,('local_neck_with_all_allocations',angle)

R=7.;pools={};trials=[];saved={};required=6.9342
for pin in range(1,5):
    e=ctx.port_pins['motion_J5']['pins'][str(pin)]
    axis=ctx.port_pins['motion_J5']['axis'];assert np.allclose(axis,[0,0,1])
    a=e+axis*5.;straight=np.linspace(e,a,101)
    straight_hit=ctx.clear(straight,ignore={'Plug_motion_J5'})
    top=a[2]+R
    entries=[];entry_fail=Counter()
    for az in range(0,360,15):
        h=np.array([math.cos(math.radians(az)),math.sin(math.radians(az)),0.])
        tt=np.linspace(0,math.pi/2,121)
        entry=np.array([a+R*(1-math.cos(t))*h+[0,0,R*math.sin(t)] for t in tt])
        err=R*(1-math.cos((tt[1]-tt[0])/2));hit=ctx.clear(entry,err)
        if hit:entry_fail[hit['object']]+=1
        else:entries.append((az,h,entry,err))
    for angle in sorted(necks):
        pool=[];counts=Counter();blockers=Counter();examples={}
        radial=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle)),0.])
        lower_z=neck_parameters[angle]['lower_z_mm'];drop=top-lower_z
        assert 0<drop<2*R
        alpha=math.acos(1-drop/(2*R));run=2*R*math.sin(alpha)
        b=necks[angle][0];assert np.linalg.norm(b-(radial*29.6+[0,0,lower_z]))<1e-8
        cend=b-radial*run+[0,0,drop]
        tt=np.linspace(0,alpha,101)
        first=np.array([cend+radial*R*math.sin(t)-[0,0,R*(1-math.cos(t))] for t in tt]);mid=first[-1]
        second=np.array([mid+radial*R*(math.sin(alpha)-math.sin(t))-[0,0,R*(math.cos(t)-math.cos(alpha))]
                         for t in np.linspace(alpha,0,101)])
        descent=np.vstack([first,second[1:]]);descent_error=R*(1-math.cos(alpha/200))
        assert np.linalg.norm(descent[-1]-b)<1e-8
        descent_hit=ctx.clear(descent,descent_error)
        if not straight_hit and not descent_hit:
            for az,h,entry,entry_error in entries:
                for bend in [7.,8.,9.,10.,12.,14.]:
                    for plan in paths(entry[-1,:2],h[:2],cend[:2],radial[:2],bend):
                        counts['tried']+=1
                        if plan['analytic_length_mm']>200:counts['length_screen']+=1;continue
                        xy=plan.pop('points_xy_mm');curve=np.column_stack([xy,np.full(len(xy),top)])
                        if np.max(np.linalg.norm(xy,axis=1))>78:counts['workspace_screen']+=1;continue
                        hit=ctx.clear(curve,plan['chord_error_mm'])
                        if hit:
                            counts['clearance_rejected']+=1;blockers[hit['object']]+=1
                            examples.setdefault(hit['object'],dict(entry_azimuth_deg=az,radius_mm=bend,family=plan['family'],hit=hit))
                            continue
                        prefix=np.vstack([straight,entry[1:],curve[1:],descent[1:]])
                        full=np.vstack([prefix,necks[angle][1:]])
                        neck_length=neck_parameters[angle]['analytic_length_mm']
                        prefix_length=5.+R*math.pi/2+plan['analytic_length_mm']+2*R*alpha
                        error=max(entry_error,descent_error,plan['chord_error_mm'],8*(1-math.cos(math.pi/400)))
                        pool.append(dict(pin=pin,azimuth_deg=angle,entry_azimuth_deg=az,planar_path=plan,
                            plane_z_mm=float(top),terminal_straight_allocation_mm=5.,
                            minimum_curvature_radius_mm=min(R,bend,8.),error_bound_mm=error,
                            analytic_prefix_length_mm=float(prefix_length),analytic_body_neck_length_mm=float(prefix_length+neck_length),
                            prefix_points=len(prefix),neck_parameters=neck_parameters[angle],curve_mm=full))
                        counts['passed']+=1
        # Retain shape diversity instead of filling the pool with the same
        # entry direction at near-identical radii; then add the shortest paths.
        pool.sort(key=lambda r:r['analytic_body_neck_length_mm'])
        chosen=[];used=set()
        for row in pool:
            key=(row['entry_azimuth_deg'],row['planar_path']['family'])
            if key not in used:chosen.append(row);used.add(key)
            if len(chosen)>=24:break
        for row in pool:
            if not any(row is x for x in chosen):chosen.append(row)
            if len(chosen)>=32:break
        key=f'{pin}_{angle}';pools[key]=[]
        for i,row in enumerate(chosen):
            cid=key+'_'+str(i);saved[cid]=row.pop('curve_mm')
            row['curve_key']=cid;pools[key].append(row)
        trials.append(dict(pin=pin,azimuth_deg=angle,status='PASS' if chosen else 'BLOCKED',
            straight_hit=straight_hit,descent_hit=descent_hit,entry_count=len(entries),entry_failures=dict(entry_fail),
            counts=dict(counts),blockers=dict(blockers),failure_examples=examples,retained=len(chosen)))
        print('OUTER_BODY_POOL',key,'valid',len(pool),'retained',len(chosen),'blockers',dict(blockers),round(time.time()-started,1),flush=True)
        (HERE/'progress.json').write_text(json.dumps(trials,ensure_ascii=False,indent=2)+'\n')

possible=[list(p) for p in itertools.permutations(sorted(necks)) if all(pools[f'{pin}_{a}'] for pin,a in enumerate(p,1))]
np.savez_compressed(HERE/'body_prefix_curves.npz',**saved)
result=dict(status='PASS' if possible else 'BLOCKED',scope='Individual body-to-neck route pools; four-line packing not yet proved',
    revision=P['revision'],**ctx.evidence(),script_sha256=sha(__file__),
    planar_math_sha256=sha(MATH),source_neck_curves_sha256=sha(neck_file),
    source_neck_parameters_sha256=sha(HERE/'selected_necks.json'),
    wire_OD_mm=.6604,surface_gap_mm=.3,required_radius_mm=required,
    pools=pools,trials=trials,possible_phase_assignments=possible,
    main_applied=False,whole_harness='BLOCKED',four_wire_packing='NOT_TESTED',
    upper_service_loop='NOT_TESTED',assembly='NOT_TESTED',supplier_cut_lengths_released=False,
    elapsed_s=time.time()-started)
ctx.assert_unchanged()
(HERE/'body_prefix_pools.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('OUTER_BODY_POOLS_DONE',result['status'],'phase assignments',len(possible),flush=True)
