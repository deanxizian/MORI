"""Test whether H01 can also be connected before CAM and bridge installation.

Preserve native endpoints and Alpha6712 reference size/radius. H02 uses its
saved lower candidate. No main CAD, PCB, hole or hardware changes are made.
"""
from pathlib import Path
H01_SCRIPT=Path(__file__).resolve();H01_A8=H01_SCRIPT.parent
H01_BOOT=H01_A8/'screen_H02_preinstalled_route.py'
__file__=str(H01_BOOT)
exec(compile(H01_BOOT.read_text().split('\nstarted=time.time();pools=',1)[0],str(H01_BOOT),'exec'),globals())
__file__=str(H01_SCRIPT)
H02_OUT=OUT;OUT=ORDER_OUT/'H01_preinstalled';OUT.mkdir(exist_ok=True)
h02_check=json.loads((H02_OUT/'verification.json').read_text());assert h02_check['status']=='PASS'
h02_mesh=json.loads((H02_OUT/'wire_solids.json').read_text())
assert h02_check['wire_solids_sha256']==sha(H02_OUT/'wire_solids.json')
for n,r in h02_mesh.items():
    m=manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64)))
    static['fixed_wire_'+n]=data(m)
for n in ['H01_1','H01_2']:static.pop('fixed_wire_'+n)
HOD=1.143;R=5.715;SAG=.01
old_pools=json.loads((A2/'ecowire_candidate.json').read_text())['candidate_pools']
segment_code=(A2/'select_joint.py').read_text()
segment_code=segment_code[segment_code.index('def exact_segment_min'):segment_code.index('selected=search')]
segment_code=segment_code.replace('valid=det>1e-12','valid=det>np.maximum(aa*cc*1e-14,1e-24)')
exec(segment_code,globals())
exact_CAM={(stage,idx,pin):transform_points(p,bt) for stage,idx,st,bt in coarse for pin,p in wire.items()}

def curve_controls(row):
    for old in old_pools[row['id']]:yield np.array(old['controls_mm'])
    e=np.array(row['curve_mm'][0]);f=np.array(row['curve_mm'][-1])
    a=e+[0,0,5];b=f+[0,0,5]
    for za,zb,y in itertools.product([141.45,142.,142.5,143.,143.5],
                                     [141.45,142.,142.5,143.,143.5],[-42.,-44.,-46.,-48.,-50.,-52.,-54.,-56.,-58.]):
        yield np.array([a,[a[0],a[1],za],[a[0],y,za],[b[0],y,zb],[b[0],b[1],zb],b])
    # Larger inward/outward offsets are a distinct lane, never a changed pin.
    for z,x,y in itertools.product([141.5,142.5,143.5],[-48.,-46.,-22.,-20.],[-42.,-46.,-50.,-54.,-58.]):
        yield np.array([a,[a[0],a[1],z],[x,a[1],z],[x,y,z],[b[0],y,z],[b[0],b[1],z],b])
    # The earlier family used only the rear of the bridge. The front corridor
    # is a different topology relative to the CAM body leads, with fixed pins.
    for za,zb,y in itertools.product([141.5,142.5,143.5,144.5,145.5],
                                     [141.5,142.5,143.5,144.5,145.5],
                                     [16.,20.,24.,28.,32.,36.,40.,44.,48.]):
        yield np.array([a,[a[0],a[1],za],[a[0],y,za],[b[0],y,zb],[b[0],b[1],zb],b])
    for za,zb,y,x in itertools.product([141.5,142.5,143.5],[141.5,142.5,143.5,144.5,145.5],
                                       [20.,28.,36.,44.],[38.,42.,46.,50.,54.]):
        yield np.array([a,[a[0],a[1],za],[a[0],y,za],[x,y,zb],[x,b[1],zb],[b[0],b[1],zb],b])

def assembly_h01(full,p):
    allowance=HOD/2+OD/2+MARGIN_H+max(np.linalg.norm(np.diff(p,axis=0),axis=1))/2+SAG+.0001
    for stage,idx,pin,lo,hi,kd,error in cam_obstacles:
        a=allowance+error;mask=np.all(p>=lo-a,axis=1)&np.all(p<=hi+a,axis=1)
        possible=False
        for point in p[mask]:
            dist=float(kd.find(point)[2])
            if dist<a:possible=True;break
        if possible:
            # A coarse nearest-sample bound may reject a narrow valid route.
            # Resolve it with true segment distances on the saved polylines,
            # retaining both source-curve chord bounds and the same 0.3 gap.
            q=exact_CAM[stage,idx,pin]
            need=HOD/2+OD/2+MARGIN_H+SAG+lengths[pin-1]['curve_chord_error_mm']+.0001
            lo=full.min(0)-need;hi=full.max(0)+need
            ids=np.flatnonzero(np.all(np.maximum(q[:-1],q[1:])>=lo,axis=1)&np.all(np.minimum(q[:-1],q[1:])<=hi,axis=1))
            if len(ids):
                for run in np.split(ids,np.flatnonzero(np.diff(ids)>1)+1):
                    distance,indices=exact_segment_min(full,q[run[0]:run[-1]+2])
                    if distance<need:return dict(stage=stage,index=idx,obstacle='CAM_wire_'+str(pin),
                        distance_mm=distance,required_mm=need,method='source_polyline_segment_distance_with_chord_bounds')
    for stage,idx,targets in moving_solids:
        hit=check_curve(p,targets,rad=HOD/2)
        if hit:return dict(stage=stage,index=idx,**hit)
    return None

started=time.time();pools={};rows=[]
for pin in [1,2]:
    key='H01_'+str(pin);row=prior[key];counts=Counter();blocks=Counter();pool=[];examples={}
    for cp in curve_controls(row):
        counts['controls']+=1;curve=rounded(cp,R)
        if curve is None:counts['short_bends']+=1;continue
        maximum_sag=0.
        for a,b,c in zip(cp,cp[1:],cp[2:]):
            u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
            theta=math.acos(np.clip(u@v,-1,1));steps=max(3,int(R*theta/.5)+1)-1
            maximum_sag=max(maximum_sag,R*(1-math.cos(theta/(2*steps))))
        if maximum_sag>SAG:counts['curve_error_bound_reject']+=1;continue
        full=np.vstack([row['curve_mm'][0],curve,row['curve_mm'][-1]])
        p=resample(full,STEP_H)
        hit=check_curve(p,static,row['from_port'],row['to_port'],rad=HOD/2)
        if hit:
            counts['static_failed']+=1;blocks['static:'+hit['obstacle']]+=1
            examples.setdefault('static:'+hit['obstacle'],hit);continue
        counts['static_passed']+=1;hit=assembly_h01(full,p)
        if hit:
            counts['assembly_failed']+=1;blocks['assembly:'+hit['obstacle']]+=1
            examples.setdefault('assembly:'+hit['obstacle'],hit);continue
        length=float(np.linalg.norm(np.diff(cp,axis=0),axis=1).sum())+10
        for a,b,c in zip(cp,cp[1:],cp[2:]):
            u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b);th=math.acos(np.clip(u@v,-1,1))
            length+=R*(th-2*math.tan(th/2))
        pool.append(dict(row,controls_mm=cp.tolist(),curve_mm=full.tolist(),analytic_length_mm=length,
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),analytic_bend_radius_mm=R))
        counts['passed']+=1
    pools[key]=sorted(pool,key=lambda r:r['analytic_length_mm'])[:60]
    rows.append(dict(id=key,status='PASS' if pool else 'BLOCKED',counts=dict(counts),blockers=dict(blocks),examples=examples))
    print('H01_PREINSTALL',key,rows[-1]['status'],dict(counts),dict(blocks),flush=True)
selected=None;best_gap=-math.inf
for a,b in itertools.product(pools['H01_1'],pools['H01_2']):
    distance,indices=exact_segment_min(a['curve_mm'],b['curve_mm']);gap=distance-HOD-2*SAG-.0001
    best_gap=max(best_gap,gap)
    if gap>=.3:
        cost=a['analytic_length_mm']+b['analytic_length_mm']
        if selected is None or cost<selected['total_nominal_length_mm']:
            selected=dict(routes=[a,b],total_nominal_length_mm=cost,pair_gap_lower_bound_mm=gap,segment_indices=indices)
report=dict(status='PASS' if selected else 'BLOCKED',scope='Bounded H01 route screening for preinstallation; no universal impossibility claim',
    script_sha256=sha(H01_SCRIPT),helper_sha256=sha(H01_BOOT),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [H02_OUT/'verification.json',H02_OUT/'wire_solids.json',A2/'ecowire_candidate.json',A2/'ecowire_joint.json']},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],other_fixed_wire_count=12,coarse_assembly_positions=len(coarse),
    route_families=['source_rear','varied_rear_height','side_lane','front_of_bridge','front_right_approach'],
    rows=rows,pools=pools,selected=selected,best_pair_gap_lower_bound_mm=best_gap if math.isfinite(best_gap) else None,
    wire_OD_mm=HOD,required_radius_mm=R,clearance_mm=.3,terminal_exits='ASSUMED',
    main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('H01_PREINSTALL_DONE',report['status'],report['best_pair_gap_lower_bound_mm'],round(time.time()-started,2),flush=True)
