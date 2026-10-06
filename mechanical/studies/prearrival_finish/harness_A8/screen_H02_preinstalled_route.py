"""Independent H02 routing study: keep both plugs connected before CAM fitting.

Only the two unselected wire curves may change. Native pins, the main model,
and all hardware remain fixed. A passing finite search is not release evidence.
"""
from pathlib import Path
ENTRY=Path(__file__).resolve();A8=ENTRY.parent
HELPER=A8/'screen_CAM_body_install_order.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\nstarted=time.time();trials=',1)[0],str(HELPER),'exec'),globals())
__file__=str(ENTRY)
from collections import Counter
from mathutils.kdtree import KDTree
OUT=ORDER_OUT/'H02_preinstalled';OUT.mkdir(exist_ok=True)
A2=A8.parent/'harness_A2'
source_routes=json.loads((A2/'ecowire_joint.json').read_text())['routes']
prior={r['id']:r for r in source_routes}
R=5.08;HOD=1.016;MARGIN_H=.3;SAG=.01;STEP_H=.16

def data(m):
    a=m.to_mesh64();v=np.asarray(a.vert_properties[:,:3]);f=np.asarray(a.tri_verts)
    return m,v.min(0),v.max(0),BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)

static={n:data(m) for n,m in phys.items()}
static.update({'Plug_'+n:data(s.m) for n,s in plug.items()})
static.update({'fixed_wire_'+n:(r['m'],r['lo'],r['hi'],r['tree']) for n,r in fixed.items() if not n.startswith('H02_')})

def check_curve(points,targets,from_port=None,to_port=None,rad=HOD/2,extra=SAG):
    d=np.linalg.norm(np.diff(points,axis=0),axis=1);s=np.r_[0.,d.cumsum()]
    allowance=rad+MARGIN_H+max(d)/2+extra+.0001
    for n,(m,lo,hi,tree) in targets.items():
        mask=np.all(points>=lo-allowance,axis=1)&np.all(points<=hi+allowance,axis=1)
        if n=='Plug_'+str(from_port):mask &= s>5.
        if n=='Plug_'+str(to_port):mask &= s<s[-1]-5.
        indices=np.flatnonzero(mask)
        for idx in indices:
            p=points[idx];dist=float(tree.find_nearest(Vector(p))[3])
            if dist<allowance:return dict(obstacle=n,point_mm=p.tolist(),distance_mm=dist,required_mm=allowance)
        starts=indices[np.r_[True,np.diff(indices)>1]] if len(indices) else []
        for idx in starts:
            p=points[idx]
            if np.all(p>=lo) and np.all(p<=hi):
                probe=manifold.Manifold.sphere(.005,12).translate(p.tolist())
                if (probe^m).volume()>probe.volume()/2:return dict(obstacle=n,inside=True,point_mm=p.tolist())
    return None

coarse=[]
for stage,poses in stages:
    for idx,(st,bt) in enumerate(poses):coarse.append((stage,idx,st,bt))
cam_obstacles=[]
for stage,idx,st,bt in coarse:
    for pin,p in wire.items():
        q=transform_points(resample(p,.1),bt)
        kd=KDTree(len(q))
        for i,v in enumerate(q):kd.insert(v,i)
        kd.balance()
        cam_obstacles.append((stage,idx,pin,q.min(0),q.max(0),kd,
            max(np.linalg.norm(np.diff(q,axis=0),axis=1))/2+lengths[pin-1]['curve_chord_error_mm']))
moving_solids=[]
for stage,idx,st,bt in coarse:
    rows={}
    for n in upper|bridge:
        rows[n]=data(phys[n].transform((st if n in upper else bt)[:3,:4]))
    rows['moving_CAM_PH']=data(housing.transform(bt[:3,:4]))
    moving_solids.append((stage,idx,rows))

def assembly_check(p):
    allowance=HOD/2+OD/2+MARGIN_H+max(np.linalg.norm(np.diff(p,axis=0),axis=1))/2+SAG+.0001
    for stage,idx,pin,lo,hi,kd,error in cam_obstacles:
        a=allowance+error
        mask=np.all(p>=lo-a,axis=1)&np.all(p<=hi+a,axis=1)
        for pt in p[mask]:
            dist=float(kd.find(pt)[2])
            if dist<a:return dict(stage=stage,index=idx,obstacle='CAM_wire_'+str(pin),distance_mm=dist,required_mm=a)
    for stage,idx,targets in moving_solids:
        hit=check_curve(p,targets)
        if hit:return dict(stage=stage,index=idx,**hit)
    return None

def controls_for(row):
    e=np.array(row['curve_mm'][0]);f=np.array(row['curve_mm'][-1])
    a=e+[0,0,5];b=f+[0,0,5]
    # Bounded low horizontal/oblique families; not an exhaustive search.
    for z in [140.8,141.,141.3,141.6,142.,142.5,143.]:
        yield [a,[a[0],a[1],z],[b[0],b[1],z],b]
        for x,y in itertools.product([30.,33.,36.,39.,42.],[-28.,-25.,-22.,-19.]):
            yield [a,[a[0],a[1],z],[x,y,z],[b[0],b[1],z],b]
    for za,zb,x,y in itertools.product([140.8,141.3,141.8,142.3],
                                      [140.,140.8,141.6,142.4],
                                      [30.,34.,38.,42.],[-28.,-24.,-20.]):
        yield [a,[a[0],a[1],za],[x,y,(za+zb)/2],[b[0],b[1],zb],b]

started=time.time();pools={};rows=[]
for pin in [1,2]:
    key='H02_'+str(pin);row=prior[key];counts=Counter();blocks=Counter();pool=[];examples={}
    for cp in controls_for(row):
        counts['controls']+=1
        cp=np.array(cp);curve=rounded(cp,R)
        if curve is None:counts['short_bends']+=1;continue
        full=np.vstack([row['curve_mm'][0],curve,row['curve_mm'][-1]])
        pts=resample(full,STEP_H)
        fail=check_curve(pts,static,row['from_port'],row['to_port'])
        if fail:
            counts['static_failed']+=1;blocks['static:'+fail['obstacle']]+=1
            examples.setdefault('static:'+fail['obstacle'],fail);continue
        counts['static_passed']+=1
        fail=assembly_check(pts)
        if fail:
            counts['assembly_failed']+=1;blocks['assembly:'+fail['obstacle']]+=1
            examples.setdefault('assembly:'+fail['obstacle'],fail);continue
        length=float(np.linalg.norm(np.diff(cp,axis=0),axis=1).sum())+10
        for a,b,c in zip(cp,cp[1:],cp[2:]):
            u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b)
            th=math.acos(np.clip(u@v,-1,1));length+=R*(th-2*math.tan(th/2))
        candidate=dict(row,controls_mm=cp.tolist(),curve_mm=full.tolist(),
                       geometric_centerline_length_mm=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum()),
                       analytic_length_mm=length,analytic_bend_radius_mm=R)
        pool.append(candidate);counts['passed']+=1
    pools[key]=sorted(pool,key=lambda r:r['analytic_length_mm'])[:60]
    rows.append(dict(id=key,status='PASS' if pool else 'BLOCKED',counts=dict(counts),blockers=dict(blocks),examples=examples))
    print('H02_PREINSTALL',key,rows[-1]['status'],dict(counts),flush=True)

segment_code=(A2/'select_joint.py').read_text()
segment_code=segment_code[segment_code.index('def exact_segment_min'):segment_code.index('selected=search')]
segment_code=segment_code.replace('valid=det>1e-12','valid=det>np.maximum(aa*cc*1e-14,1e-24)')
exec(segment_code,globals())
selected=None;best_gap=-math.inf
for a,b in itertools.product(pools['H02_1'],pools['H02_2']):
    distance,indices=exact_segment_min(a['curve_mm'],b['curve_mm'])
    gap=distance-HOD-2*SAG-.0001
    best_gap=max(best_gap,gap)
    if gap>=.3:
        cost=a['analytic_length_mm']+b['analytic_length_mm']
        if selected is None or cost<selected['total_nominal_length_mm']:
            selected=dict(routes=[a,b],total_nominal_length_mm=cost,pair_gap_lower_bound_mm=gap,segment_indices=indices)
out=dict(status='PASS' if selected else 'BLOCKED',scope='Bounded two-wire H02 preinstallation candidate; finite coarse assembly only',
    source_main_sha256=source_hash,protected_sources=protected,script_sha256=sha(ENTRY),helper_sha256=sha(HELPER),
    substituted_unadopted_prints=membership['substituted_unadopted_prints'],
    source_routes_sha256=sha(A2/'ecowire_joint.json'),other_fixed_wire_count=12,
    static_source_objects=209,mating_allocations=len(plug),coarse_assembly_positions=len(coarse),
    rows=rows,pools=pools,selected=selected,best_pair_gap_lower_bound_mm=best_gap if math.isfinite(best_gap) else None,
    required_radius_mm=R,wire_OD_mm=HOD,clearance_mm=.3,main_applied=False,
    terminal_exit_geometry='ASSUMED',full_attached_harness_assembly='NOT_TESTED',
    later_H01_H04_installation='NOT_TESTED',whole_harness='BLOCKED',manufacturing_release=False,elapsed_s=time.time()-started)
(OUT/'screen.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('H02_PREINSTALL_DONE',out['status'],out['best_pair_gap_lower_bound_mm'],round(time.time()-started,2),flush=True)
