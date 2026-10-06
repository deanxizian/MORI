"""Choose CAM lift shapes and H02 routes together, with fixed native ends.

Reuse the bounded H02 source pools and the checked CAM bend-family lifts.
No PCB/print changes and no supplier cut lengths are produced.
"""
from pathlib import Path
JOINT_SCRIPT=Path(__file__).resolve()
JOINT_HELPER=JOINT_SCRIPT.parent/'screen_CAM_feed_lift_transition.py'
__file__=str(JOINT_HELPER)
exec(compile(JOINT_HELPER.read_text().split('\nfor pin in range(1,5):',1)[0],str(JOINT_HELPER),'exec'),globals())
__file__=str(JOINT_SCRIPT)
prior_path=OUT/'screen.json';prior=json.loads(prior_path.read_text())
assert prior['status']=='BLOCKED' and prior['script_sha256']==sha(JOINT_HELPER)
for p,h in prior['source_files'].items():assert sha(PROJECT/p)==h
h02_pool_path=ORDER_OUT/'H02_preinstalled/screen.json'
h02_pools=json.loads(h02_pool_path.read_text())
assert h02_pools['status']=='PASS'
assert h02_pools['script_sha256']==sha(JOINT_SCRIPT.parent/'screen_H02_preinstalled_route.py')
OUT=ORDER_OUT/'CAM_H02_joint_lift';OUT.mkdir(exist_ok=True)
for name in ['fixed_wire_H02_1','fixed_wire_H02_2']:
    assert target_data.pop(name)
base_variant=variant_curve

# Existing pass records checked more fixed obstacles than remain here.
# Rebuild their saved parametric recipes without rerunning unchanged checks.
rebuild_path=JOINT_SCRIPT.parent/'screen_CAM_feed_lift_schedule.py'
rebuild=rebuild_path.read_text().split('\nfor pin in range(1,4):',1)[1].split('\n# The original pin-4 LSL family',1)[0]
exec(compile('for pin in range(1,4):'+rebuild,str(rebuild_path),'exec'),globals())
pin4_results=[];pools[4]=[]
for candidate in screen['pools']['4']:
    if candidate['parameters']['family']!='LSL':continue
    row=check_candidate(4,candidate)
    pin4_results.append(row)
    if row['status']=='PASS':pools[4].append(row)
print('CAM_H02_FREE_PIN4',len(pools[4]),'of',len(pin4_results),round(time.time()-started,2),flush=True)

pair_functions=JOINT_HELPER.read_text().split('\npair_cache = {}',1)[1].split('\nsearch_nodes=0',1)[0]
exec(compile('pair_cache = {}'+pair_functions,str(JOINT_HELPER),'exec'),globals())


def dense(points,step=.06):
    p=np.asarray(points);d=np.diff(p,axis=0)
    counts=np.maximum(1,np.ceil(np.linalg.norm(d,axis=1)/step).astype(int))
    ids=np.repeat(np.arange(len(counts)),counts)
    before=np.r_[0,np.cumsum(counts)[:-1]]
    t=(np.arange(int(counts.sum()))-np.repeat(before,counts))/counts[ids]
    return np.vstack([p[ids]+d[ids]*t[:,None],p[-1]])


HOD=1.016;HSAG=.01
routes={}
for name,items in h02_pools['pools'].items():
    for index,row in enumerate(items):
        key=name+'_pool'+str(index)
        p=dense(row['curve_mm'])
        routes[key]=dict(key=key,id=name,source_pool_index=index,row=row,points=p,
                         halfstep=float(max(np.linalg.norm(np.diff(p,axis=0),axis=1))/2))
cam_trees={};route_cam_cache={};route_pair_cache={}


def route_cam_check(route,cam):
    key=(route['key'],cam['candidate_id'])
    if key in route_cam_cache:return route_cam_cache[key]
    minimum=math.inf;failure=None
    for index,c in enumerate(curve_cache[cam['candidate_id']]):
        tree_key=(cam['candidate_id'],index)
        if tree_key not in cam_trees:
            kd=KDTree(len(c['points']))
            for i,p in enumerate(c['points']):kd.insert(p,i)
            kd.balance();cam_trees[tree_key]=kd
        kd=cam_trees[tree_key]
        err=route['halfstep']+float(max(np.linalg.norm(np.diff(c['points'],axis=0),axis=1))/2)+HSAG+c['curve_chord_error_mm']+.0001
        required=HOD/2+OD/2+MARGIN+err
        lo=c['points'].min(0);hi=c['points'].max(0)
        mask=np.all(route['points']>=lo-required,axis=1)&np.all(route['points']<=hi+required,axis=1)
        for p in route['points'][mask]:
            distance=float(kd.find(p)[2]);gap=distance-HOD/2-OD/2-err
            minimum=min(minimum,gap)
            if gap<MARGIN:
                failure=dict(index=index,bridge_z_mm=float(u_values[index]*18.),
                             sampled_gap_bound_mm=gap)
                break
        if failure:break
    result=dict(status='BLOCKED' if failure else 'PASS',failure=failure,
                minimum_near_sample_gap_bound_mm=minimum if math.isfinite(minimum) else None,
                complete_minimum=False)
    route_cam_cache[key]=result
    return result


segment_path=JOINT_SCRIPT.parent.parent/'harness_A2/select_joint.py'
segment_code=segment_path.read_text()
segment_code=segment_code[segment_code.index('def exact_segment_min'):segment_code.index('selected=search')]
segment_code=segment_code.replace('valid=det>1e-12','valid=det>np.maximum(aa*cc*1e-14,1e-24)')
exec(compile(segment_code,str(segment_path),'exec'),globals())


def h02_pair(a,b):
    key=(a['key'],b['key'])
    if key in route_pair_cache:return route_pair_cache[key]
    distance,indices=exact_segment_min(a['row']['curve_mm'],b['row']['curve_mm'])
    gap=float(distance-HOD-2*HSAG-.0001)
    result=dict(status='PASS' if gap>=MARGIN else 'BLOCKED',surface_gap_bound_mm=gap,
                segment_indices=indices)
    route_pair_cache[key]=result
    return result


order=sorted(pools,key=lambda pin:len(pools[pin]))
search_nodes=0;NODE_LIMIT=20000
first_pair_failures=[]


def search(chosen,available):
    global search_nodes
    search_nodes+=1
    if search_nodes>NODE_LIMIT:return None
    if len(chosen)==4:
        for a,b in itertools.product(available['H02_1'],available['H02_2']):
            if h02_pair(a,b)['status']=='PASS':return dict(cam=chosen,h02=[a,b])
        return None
    for c in pools[order[len(chosen)]]:
        if not all(pair_check(p,c)['status']=='PASS' for p in chosen):continue
        reduced={name:[r for r in values if route_cam_check(r,c)['status']=='PASS']
                 for name,values in available.items()}
        if not all(reduced.values()):continue
        result=search(chosen+[c],reduced)
        if result:return result
    return None


available={name:[r for r in routes.values() if r['id']==name] for name in ['H02_1','H02_2']}
chosen=search([],available) if all(pools.values()) else None
saved={};selected=None
if chosen:
    cam=chosen['cam'];h02=chosen['h02']
    for c in cam:
        for i,curve in enumerate(curve_cache[c['candidate_id']]):saved[f"pin{c['pin']}_pose{i}"]=curve['points']
    selected=dict(cam=cam,h02=[dict(key=r['key'],source_pool_index=r['source_pool_index'],**r['row']) for r in h02],
                  h02_pair=h02_pair(*h02),
                  cam_pairs=[dict(a=a['candidate_id'],b=b['candidate_id'],**pair_check(a,b)) for a,b in itertools.combinations(cam,2)],
                  route_cam_pairs=[dict(h02=r['key'],cam=c['candidate_id'],**route_cam_check(r,c)) for r,c in itertools.product(h02,cam)])
np.savez_compressed(OUT/'curves.npz',**saved)
report=dict(status='PASS' if chosen else 'BLOCKED',
            scope='Joint six-wire finite bridge lift only; H02 installation and other phases must be rechecked',
            script_sha256=sha(JOINT_SCRIPT),helper_sha256=sha(JOINT_HELPER),
            protected_sources=protected,source_main_sha256=source_hash,
            source_files={**prior['source_files'],str(prior_path.relative_to(PROJECT)):sha(prior_path),
                          str(h02_pool_path.relative_to(PROJECT)):sha(h02_pool_path),
                          str(rebuild_path.relative_to(PROJECT)):sha(rebuild_path),
                          str(segment_path.relative_to(PROJECT)):sha(segment_path)},
            planned_positions=STEPS,sample_spacing_mm=.5,bridge_lift_mm=18.,
            shell_transform=fixed_shell.tolist(),source_prints=membership['substituted_unadopted_prints'],
            fixed_body_wires_total=14,replaced_h02_routes=2,cam_wires=4,native_endpoints_unchanged=True,
            H02_radius_mm=5.08,H02_OD_mm=HOD,CAM_minimum_radius_mm=7.,CAM_OD_mm=OD,
            pin4_results=pin4_results,cam_pool_sizes={str(k):len(v) for k,v in pools.items()},
            h02_pool_sizes={k:len(v) for k,v in h02_pools['pools'].items()},
            search_nodes=search_nodes,node_limit=NODE_LIMIT,search_budget_exceeded=search_nodes>NODE_LIMIT,
            selected=selected,curves_sha256=sha(OUT/'curves.npz'),
            cam_pair_diagnostics=[dict(a=k[0],b=k[1],**v) for k,v in pair_cache.items()],
            h02_cam_diagnostics=[dict(h02=k[0],cam=k[1],**v) for k,v in route_cam_cache.items()],
            h02_pair_diagnostics=[dict(a=k[0],b=k[1],**v) for k,v in route_pair_cache.items()],
            H02_open_deck_recheck='NOT_TESTED',H02_full_head_recheck='NOT_TESTED',
            remaining_bridge_stages='NOT_TESTED',continuous_movement='NOT_TESTED',
            actual_wire_terminal_and_hands='NOT_TESTED',main_applied=False,
            whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('CAM_H02_COPACKING_DONE',report['status'],search_nodes,
      None if not selected else ([c['candidate_id'] for c in selected['cam']],[r['key'] for r in selected['h02']]),
      round(time.time()-started,2),flush=True)
