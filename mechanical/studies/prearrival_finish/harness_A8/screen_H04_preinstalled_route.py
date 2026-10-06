"""Bounded lowered IMU-curve study before CAM installation.

Keep all native endpoints, 5 mm straight terminal legs and reference R5.08.
No CAD or PCB changes. Individual curves do not prove an eight-wire assembly.
"""
from pathlib import Path
ENTRY4=Path(__file__).resolve();A84=ENTRY4.parent;BOOT4=A84/'screen_H02_preinstalled_route.py'
__file__=str(BOOT4)
exec(compile(BOOT4.read_text().split('\nstarted=time.time();pools=',1)[0],str(BOOT4),'exec'),globals())
__file__=str(ENTRY4)
H02_OUT=OUT;OUT=ORDER_OUT/'H04_preinstalled';OUT.mkdir(exist_ok=True)
for n in list(static):
    if n.startswith('fixed_wire_H04_'):static.pop(n)
h02_check=json.loads((H02_OUT/'verification.json').read_text());assert h02_check['status']=='PASS'
assert h02_check['wire_solids_sha256']==sha(H02_OUT/'wire_solids.json')
for n,r in json.loads((H02_OUT/'wire_solids.json').read_text()).items():
    static['fixed_wire_'+n]=data(manifold.Manifold(manifold.Mesh64(np.array(r['vertices_mm']),np.array(r['triangles'],dtype=np.uint64))))
imu_path=A2/'imu_axial_complete_joint_diagnostic.json';imu=json.loads(imu_path.read_text())
original={r['id']:r for r in imu['routes']}
segment_code=(A2/'select_joint.py').read_text()
segment_code=segment_code[segment_code.index('def exact_segment_min'):segment_code.index('selected=search')]
segment_code=segment_code.replace('valid=det>1e-12','valid=det>np.maximum(aa*cc*1e-14,1e-24)')
exec(segment_code,globals())
exact_CAM={(stage,idx,pin):transform_points(p,bt) for stage,idx,st,bt in coarse for pin,p in wire.items()}
sequence_helper=A84/'screen_H01_preinstalled_route.py';sequence_source=sequence_helper.read_text()
sequence_source=sequence_source[sequence_source.index('def assembly_h01'):sequence_source.index('\nstarted=time.time();pools=')]
exec(compile(sequence_source,str(sequence_helper),'exec'),globals())
gauss_t,gauss_w=np.polynomial.legendre.leggauss(64);gauss_t=(gauss_t+1)/2

def controls4(row):
    old=np.array(row['cubic_controls_mm']);yield old
    ratio=np.linalg.norm(old[1,1]-old[1,0])/np.linalg.norm(old[0,3]-old[0,2])
    assert np.linalg.norm((old[1,1]-old[1,0])-ratio*(old[0,3]-old[0,2]))<1e-7
    for up,dz,dy in itertools.product([8.,10.,12.,14.,16.],[-18.,-15.,-12.,-9.,-6.,-3.,0.],[-2.,0.,2.]):
        c=old.copy();c[0,1]=c[0,0]+[0,0,up];c[0,2]+=np.array([0,dy,dz])
        c[1,1]=c[1,0]+ratio*(c[0,3]-c[0,2]);yield c

def length4(c):
    total=10.
    for p in c:
        t=gauss_t[:,None];u=1-t
        d=3*(u*u*(p[1]-p[0])+2*u*t*(p[2]-p[1])+t*t*(p[3]-p[2]))
        total+=float(np.sum(gauss_w*np.linalg.norm(d,axis=1))/2)
    return total

started=time.time();pools={};rows=[]
for key,row in sorted(original.items()):
    counts=Counter();blocks=Counter();examples={};pool=[]
    for c in controls4(row):
        counts['controls']+=1
        if min(radius_at_samples(p) for p in c)<R+.02:counts['sample_curvature_reject']+=1;continue
        extrema=[extrema_radius(p) for p in c];minimum=min(r[0] for r in extrema)
        if minimum<R+.02:counts['nominal_extrema_reject']+=1;continue
        bound=max(max(np.linalg.norm(6*(p[2]-2*p[1]+p[0])),np.linalg.norm(6*(p[3]-2*p[2]+p[1]))) for p in c)/(8*180**2)
        if bound>SAG:counts['curve_error_reject']+=1;continue
        curve=np.vstack([bezier(c[0],np.linspace(0,1,181)),bezier(c[1],np.linspace(0,1,181))[1:]])
        full=np.vstack([row['curve_mm'][0],curve,row['curve_mm'][-1]])
        points=resample(full,STEP_H)
        hit=check_curve(points,static,row['from_port'],row['to_port'],rad=HOD/2)
        if hit:
            counts['static_failed']+=1;blocks['static:'+hit['obstacle']]+=1
            examples.setdefault('static:'+hit['obstacle'],hit);continue
        counts['static_passed']+=1;hit=assembly_h01(full,points)
        if hit:
            counts['assembly_failed']+=1;blocks['assembly:'+hit['obstacle']]+=1
            examples.setdefault('assembly:'+hit['obstacle'],hit);continue
        item=dict(row,cubic_controls_mm=c.tolist(),curve_mm=full.tolist(),
            minimum_curvature_radius_mm=minimum,curvature_extrema_parameters=[r[1] for r in extrema],
            curve_chord_error_bound_mm=bound,reference_length_mm=length4(c),
            geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
            control_displacement_score=float(np.linalg.norm(c-np.array(row['cubic_controls_mm']),axis=2).sum()))
        pool.append(item);counts['passed']+=1
    pools[key]=sorted(pool,key=lambda r:r['control_displacement_score'])[:12]
    rows.append(dict(id=key,status='PASS' if pool else 'BLOCKED',counts=dict(counts),blockers=dict(blocks),examples=examples))
    print('H04_PREINSTALL',key,rows[-1]['status'],dict(counts),dict(blocks),flush=True)

order=sorted(pools,key=lambda key:len(pools[key]));cache={};chosen={};calls=0;search_started=time.time()
def fits(a,ia,b,ib):
    global calls
    key=(a,ia,b,ib)
    if key not in cache:
        calls+=1;ar=pools[a][ia];br=pools[b][ib]
        distance,indices=exact_segment_min(ar['curve_mm'],br['curve_mm'])
        cache[key]=distance-HOD-ar['curve_chord_error_bound_mm']-br['curve_chord_error_bound_mm']-.0001>=.3
    return cache[key]
def search(depth):
    if depth==len(order):return True
    if time.time()-search_started>60:return False
    key=order[depth]
    for index in range(len(pools[key])):
        if all(fits(key,index,other,j) for other,j in chosen.items()):
            chosen[key]=index
            if search(depth+1):return True
            chosen.pop(key)
    return False
found=all(pools.values()) and search(0)
selected=[pools[k][chosen[k]] for k in sorted(chosen)] if found else None
report=dict(status='PASS' if found else 'BLOCKED',scope='Bounded lowered H04 cubic candidates and finite coarse assembly; no physical release',
    script_sha256=sha(ENTRY4),helper_sha256=sha(BOOT4),sequence_helper_sha256=sha(sequence_helper),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [imu_path,H02_OUT/'verification.json',H02_OUT/'wire_solids.json']},
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],other_fixed_wire_count=6,
    source_objects=209,mating_allocations=len(plug),coarse_assembly_positions=len(coarse),
    rows=rows,pools=pools,selected=selected,pairwise_search_calls=calls,pairwise_time_limit_s=60,
    reference_radius_mm=R,wire_OD_mm=HOD,terminal_exits='ASSUMED',curvature_method='Numerical polynomial extrema; not interval certified',
    open_body_attached_installation='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    no_universal_impossibility_claim=True,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('H04_PREINSTALL_DONE',report['status'],calls,round(time.time()-started,2),flush=True)
