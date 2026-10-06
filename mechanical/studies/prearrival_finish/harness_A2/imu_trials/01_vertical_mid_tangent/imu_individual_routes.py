# -*- coding: utf-8 -*-
"""Generate numbered single-wire IMU route pools without structural changes."""
from pathlib import Path
import json,hashlib,time,itertools,collections
A4STUDY=Path(__file__).resolve().parent
__file__=str(A4STUDY/'check_static.py')
exec(compile(Path(__file__).read_text().split('specs=[')[0],__file__,'exec'),globals())
assert ECOWIRE
from numpy.polynomial import polynomial as poly

base=json.loads((A4STUDY/'ecowire_joint.json').read_text())
assert base['source_blend_sha256']==source_hash and base['status']=='PASS'
existing=[]
for row in base['routes']:
    pts=np.asarray(row['curve_mm']);existing.append((row,pts[:-1],np.diff(pts,axis=0)))
R=5.08;OD=1.016;radius=OD/2
sample_t=np.linspace(0,1,65)
def bezier(c,t):
    c=np.asarray(c);v=t[:,None];u=1-v
    return u**3*c[0]+3*u*u*v*c[1]+3*u*v*v*c[2]+v**3*c[3]
def radius_at_samples(c):
    c=np.asarray(c);v=sample_t[:,None];u=1-v
    d=3*(u*u*(c[1]-c[0])+2*u*v*(c[2]-c[1])+v*v*(c[3]-c[2]))
    dd=6*(u*(c[2]-2*c[1]+c[0])+v*(c[3]-2*c[2]+c[1]))
    return float(np.min(np.linalg.norm(d,axis=1)**3/np.maximum(np.linalg.norm(np.cross(d,dd),axis=1),1e-12)))
def real_unit_roots(coef):
    coef=poly.polytrim(coef,tol=1e-8)
    if len(coef)<2:return []
    roots=poly.polyroots(coef/max(abs(coef)))
    return [float(q.real) for q in roots if abs(q.imag)<1e-6 and 0<q.real<1]
def extrema_radius(c):
    # Curvature squared is N/S^3, N=|d x dd|^2 and S=|d|^2.
    # Endpoints and all real roots of N'S-3NS' cover nominal extrema.
    c=np.asarray(c)
    d=np.array([3*(c[1]-c[0]),6*(c[0]-2*c[1]+c[2]),3*(-c[0]+3*c[1]-3*c[2]+c[3])]).T
    dd=np.array([d[:,1],2*d[:,2]]).T
    S=np.zeros(5)
    for v in d:S=poly.polyadd(S,poly.polymul(v,v))
    N=np.zeros(7)
    for i,j in [(1,2),(2,0),(0,1)]:
        cr=poly.polysub(poly.polymul(d[i],dd[j]),poly.polymul(d[j],dd[i]))
        N=poly.polyadd(N,poly.polymul(cr,cr))
    F=poly.polysub(poly.polymul(poly.polyder(N),S),3*poly.polymul(N,poly.polyder(S)))
    q=[0.,1.]+real_unit_roots(F)
    speed_at=[0.,1.]+real_unit_roots(poly.polyder(S))
    if min(poly.polyval(x,S) for x in speed_at)<1e-8:return 0.,q
    k2=max(max(0,float(poly.polyval(x,N)))/float(poly.polyval(x,S))**3 for x in q)
    return 1/max(k2,1e-24)**.5,q

def check_points(points):
    # <=0.24mm polyline resampling plus curvature/chord allowance.
    clear=radius+.3+.13
    for n,lo,hi in zip(obs,los,his):
        mask=np.all(points>=lo-clear,axis=1)&np.all(points<=hi+clear,axis=1)
        for p in points[mask]:
            pos,norm,_,d=trees[n].find_nearest(Vector(p))
            if d<clear or (Vector(p)-pos).dot(norm)<-.0001:return n,p.tolist()
    for row,a,v in existing:
        w=points[:,None,:]-a[None,:,:]
        t=np.clip(np.sum(w*v[None,:,:],axis=2)/np.maximum(np.sum(v*v,axis=1),1e-12),0,1)
        dist=np.linalg.norm(w-t[:,:,None]*v[None,:,:],axis=2)
        ix=np.unravel_index(np.argmin(dist),dist.shape)
        if dist[ix]<clear+row['wire_OD_max_mm']/2:return row['id'],points[ix[0]].tolist()
    return None,None

params=list(itertools.product(range(-28,-5,2),[-65.,-66.,-64.,-67.],[116.,114.,118.,112.],
    [18.,22.,26.,14.],[20.,26.,14.],[16.,22.,10.],[12.,18.,24.]))
np.random.default_rng(304).shuffle(params)
da=port_pins['motion_J4'];db=port_pins['imu_J1'];pools={};search=[]
limit=18000;pool_limit=60;start=time.time()
for pin in range(1,9):
    ea=da['pins'][str(pin)];eb=db['pins'][str(pin)]
    a=ea+5*da['axis'];b=eb+5*db['axis']
    counts=collections.Counter();blocked=collections.Counter();pool=[];keys=set()
    for x,y,z,up,h1,h2,down in params[:limit]:
        counts['tried']+=1;k=np.array([x,y,z]);tan=np.array([0.,0.,-1.])
        c1=np.array([a,a+da['axis']*up,k-tan*h1,k]);c2=np.array([k,k+tan*h2,b+db['axis']*down,b])
        if min(radius_at_samples(c1),radius_at_samples(c2))<R+.02:
            counts['curvature_reject']+=1;continue
        curve=np.vstack([bezier(c1,np.linspace(0,1,181)),bezier(c2,np.linspace(0,1,181))[1:]])
        # Preserve exact 5mm straight terminal segments. These were separately
        # checked against all other rigid objects by check_static.py.
        points=resample(curve,.24)
        name,where=check_points(points)
        if name:
            counts['space_reject']+=1;blocked[name]+=1;continue
        r1,q1=extrema_radius(c1);r2,q2=extrema_radius(c2)
        if min(r1,r2)<R+.02:counts['extrema_reject']+=1;continue
        key=(x,y,z,up,down)
        if key in keys:continue
        keys.add(key)
        full=np.vstack([ea,curve,eb]);ln=float(np.linalg.norm(np.diff(full,axis=0),axis=1).sum())
        pool.append(dict(id='H04_'+str(pin),harness='H04',pin=pin,from_port='motion_J4',to_port='imu_J1',
            curve_mm=full.tolist(),cubic_controls_mm=[c1.tolist(),c2.tolist()],
            wire_OD_max_mm=OD,required_bend_radius_mm=R,terminal_straight_mm=5,
            minimum_curvature_radius_mm=min(r1,r2),curvature_extrema_parameters=[q1,q2],
            geometric_centerline_length_mm=ln,
            method='Two tangent-continuous cubics and terminal straight segments; numerical polynomial curvature extrema'))
        if len(pool)>=pool_limit:break
    pools[str(pin)]=pool
    search.append(dict(pin=pin,**counts,candidates=len(pool),blockers=dict(blocked)))
    print('IMU_SINGLE_POOL',search[-1],flush=True)
    (A4STUDY/'imu_individual_progress.json').write_text(json.dumps(search,ensure_ascii=False,indent=2)+'\n')
out=dict(revision=P['revision'],source_blend_sha256=source_hash,
    source_six_wire_sha256=hashlib.sha256((A4STUDY/'ecowire_joint.json').read_bytes()).hexdigest(),
    status='PASS' if all(pools.values()) else 'BLOCKED',scope='Individual route pools only; eight-wire packing and solid audit pending',
    pools=pools,search=search,elapsed_s=time.time()-start,main_modified=False,cut_lengths_released=False,
    limitations=['Alpha6711 remains an unselected static wire candidate.',
        'Terminal lateral exit geometry remains assumed from mating housing; pin numbering/pitch remain native.',
        'No strain-relief, service slack, cable-attached removal or complete harness qualification.',
        'Candidates screened against saved M1.47 solids and six H01-H03 wires.'])
(A4STUDY/'imu_individual_pools.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('IMU_INDIVIDUAL_COMPLETE',out['status'],out['elapsed_s'],flush=True)
