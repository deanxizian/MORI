"""Finite quintic-curve search within the verified swept-solid corridor.

Staging-to-staging only. No cable construction, clamps or print changes.
"""
from pathlib import Path
import sys,json,hashlib,math,time,collections
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
HERE=Path(__file__).resolve().parent
path_file=HERE/'head_entry_shortest.json';routes=json.loads(path_file.read_text())
meshfile=HERE/'head_entry_obstacle_union.npz';mesh=np.load(meshfile)
assert hashlib.sha256(meshfile.read_bytes()).hexdigest()==routes['source_obstacle_mesh_sha256']
tree=BVHTree.FromPolygons(mesh['vertices_mm'],mesh['triangles'],all_triangles=True)
seed_row=routes['groups'][0];radius=seed_row['planning_diameter_mm']/2;gap=.3
required_bend=14.224+radius;started=time.time();rng=np.random.default_rng(20261003)

def bernstein(n,t):
    return np.stack([math.comb(n,i)*t**i*(1-t)**(n-i) for i in range(n+1)],axis=1)
tc=np.linspace(0,1,97);td=np.linspace(0,1,769)
Bc=bernstein(5,tc);Bd=bernstein(5,td);Bv=bernstein(4,td);Ba=bernstein(3,td)

def min_radius(c):
    v=Bv@(5*np.diff(c,axis=0));a=Ba@(20*np.diff(c,n=2,axis=0))
    speed=np.linalg.norm(v,axis=1);cross=np.linalg.norm(np.cross(v,a),axis=1)
    if speed.min()<1e-7:return 0.
    return float(1/max((cross/speed**3).max(),1e-20))

def clear_curve(c,dense=False):
    B=Bd if dense else Bc;p=B@c;chord=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())
    error=float(np.linalg.norm(20*np.diff(c,n=2,axis=0),axis=1).max()/(len(p)-1)**2/8)
    required=radius+gap+chord/2+error+1e-4;nearest=1e9
    for x in p:
        d=tree.find_nearest(Vector(x))[3];nearest=min(nearest,d)
        if d<required:return False,nearest-chord/2-error-1e-4-radius
    return True,nearest-chord/2-error-1e-4-radius

def fit(points):
    p=np.asarray(points);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];t=s/s[-1];B=bernstein(5,t)
    inner=np.linalg.lstsq(B[:,1:5],p-B[:,[0]]*p[0]-B[:,[5]]*p[-1],rcond=None)[0]
    return np.vstack([p[0],inner,p[-1]])

seeds=[fit(r['path_mm']) for r in routes['groups']]
seeds += [np.array([[40,8,159],[40,8,171],[29,8,164],[16,25,179],[18,28,190],[18,28,202]],float),
          np.array([[40,8,159],[39,12,166],[32,18,166],[18,25,178],[18,28,190],[18,28,202]],float)]
best=None;rejects=collections.Counter();tried=0;passing=[]
for phase in range(5):
    pool=seeds if best is None else seeds+[np.asarray(best['controls_mm'])]*4
    scale=[.25,.5,1.,2.,3.5][phase]
    for i in range(5000):
        base=pool[i%len(pool)];c=base.copy()
        c[1:5]+=rng.normal(size=(4,3))*scale
        # Endpoints remain explicit fixed staging points, not free successes.
        tried+=1
        if not clear_curve(c)[0]:rejects['coarse_clearance_bound']+=1;continue
        ok,clear=clear_curve(c,True)
        if not ok:rejects['dense_clearance_bound']+=1;continue
        R=min_radius(c)
        if best is None or R>best['sampled_minimum_curvature_radius_mm']:
            p=Bd@c
            best=dict(controls_mm=c.tolist(),curve_mm=p.tolist(),sampled_minimum_curvature_radius_mm=R,
                      source_surface_gap_lower_bound_mm=clear,polyline_length_mm=float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum()))
            print('ENTRY_SMOOTH_BEST',tried,R,clear,time.time()-started,flush=True)
        if R>=required_bend:
            passing.append(best);break
        rejects['bend_radius_below_sample_requirement']+=1
    print('ENTRY_SMOOTH_PHASE',phase,tried,len(passing),time.time()-started,flush=True)
    if passing:break

out=dict(status='PASS' if passing else 'BLOCKED',scope='Finite quintic staging-path search for largest current 4-wire planning group',
         source_blend_sha256=routes['source_blend_sha256'],source_shortest_path_sha256=hashlib.sha256(path_file.read_bytes()).hexdigest(),
         source_swept_mesh_sha256=hashlib.sha256(meshfile.read_bytes()).hexdigest(),planning_diameter_mm=radius*2,
         wire_static_bend_basis_mm=14.224,required_group_centreline_radius_mm=required_bend,
         candidates_tested=tried,rejections=dict(rejects),best_collision_free=best,selected=passing,
         simultaneous_three_groups='NOT_TESTED',loop_endpoint_connection='NOT_TESTED',pitch_loop='NOT_TESTED',
         actual_anchors='NOT_TESTED',inside_cosmetic_envelope='NOT_TESTED',main_geometry_changed=False,elapsed_s=time.time()-started,
         limits=['The endpoints are study points, not the passing body-loop endpoint or hardware connectors.',
                 'Clearance covers the continuous quintic via second-derivative and sampling bounds.',
                 'Minimum curvature is still a dense numerical sample, not a certified global bound.',
                 'No physical cable selection, within-bundle sliding, lifetime or installed sequence is established.',
                 'The fixed-yaw route clears only the sampled source pose union; complete head wiring remains unresolved.'])
(HERE/'head_entry_smooth.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('ENTRY_SMOOTH_COMPLETE',out['status'],tried,time.time()-started,flush=True)
