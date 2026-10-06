"""Bounded translation search for J18 after CAM lines, before body shells.

Each grid edge is an exact swept axis-aligned housing box. Nine other upper
wire candidates and fourteen fixed-body wire solids remain. This is a housing
approach study: J18's own attached wires and mating contact are unresolved.
"""
from pathlib import Path
import collections,heapq,itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/power_plug_simple';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import manifold
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from upper_pack_geometry import refined

ctx=Context();started=time.time();key='power_J18';plug=ctx.plug[key]
assert np.allclose(ctx.port_pins[key]['axis'],[0,0,1])
deferred={'Body_Upper','Body_Lower'}
targets={n:t for n,t in ctx.targets.items() if n not in deferred|{'Plug_'+key}}
names=list(targets);los=np.array([targets[n]['lo'] for n in names]);his=np.array([targets[n]['hi'] for n in names])
curvefile=BASE/'cam_side_fans/c6_join/candidate_curves.npz';curves=np.load(curvefile);wires={}
for name in [*[f'CAM_{i}' for i in range(1,5)],'P_J9_1','P_J9_2','P_J9_3','SPK_reservation_3','SPK_reservation_6']:
    p=refined(curves[name+'_y0'+('_p0' if name.startswith('CAM_') else '')],.02)
    rad=.3302 if name.startswith('CAM_') else .4445 if name.startswith('SPK_') else .5842
    wires[name]=dict(p=p,radius=rad,error=.0003,step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max()),lo=p.min(0),hi=p.max(0))
calls=0;obstacles=collections.Counter();cache={};min_gap=.301
def clear(a,b,mate=False):
    global calls,min_gap
    calls+=1;lo=plug.lo+np.minimum(a,b);hi=plug.hi+np.maximum(a,b)
    m=manifold.Manifold.hull_points(np.vstack([plug.v+a,plug.v+b]));mesh=m.to_mesh64();verts=np.asarray(mesh.vert_properties[:,:3]);faces=np.asarray(mesh.tri_verts);tree=BVHTree.FromPolygons(verts,faces.tolist(),all_triangles=True)
    planes=verts[faces[:,0]];normal=np.cross(verts[faces[:,1]]-planes,verts[faces[:,2]]-planes);normal/=np.linalg.norm(normal,axis=1)[:,None]
    ids=np.flatnonzero(np.all(lo<=his+.301,axis=1)&np.all(hi+.301>=los,axis=1))
    for i in ids:
        name=names[i]
        if mate and name=='Power_Module':continue
        target=targets[name]['m'];vol=float((m^target).volume());gap=float(m.min_gap(target,.301)) if abs(vol)<1e-7 else 0.
        if abs(vol)>1e-6 or gap<.3:
            obstacles[name]+=1;return dict(target=name,overlap_mm3=vol,gap_mm=gap)
    for name,w in wires.items():
        bound=w['radius']+.3+w['step']/2+w['error']+1e-4
        if not(np.all(lo<=w['hi']+bound) and np.all(hi+bound>=w['lo'])):continue
        ids=np.flatnonzero(np.all(w['p']>=lo-bound,axis=1)&np.all(w['p']<=hi+bound,axis=1))
        if len(ids)==0:continue
        p=w['p'][ids];inside=np.array([np.all(np.einsum('ij,ij->i',q-planes,normal)<=0) for q in p]);d=np.array([0. if hit else float(tree.find_nearest(Vector(q))[3]) for q,hit in zip(p,inside)]);k=int(np.argmin(d))
        if d[k]<bound:
            obstacles['wire_'+name]+=1;return dict(target='wire_'+name,point_mm=p[k].tolist(),gap_lower_bound_mm=float(d[k]-bound+.3))
    return None

source=BASE/'cam_restraints/power_plug_search';report=json.loads((source/'review.json').read_text());assert report['status']=='PASS'
for f,h in {**report['sources'],**report['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(source/'path.npz')==report['path_sha256']
p=np.load(source/'path.npz')['shifts_mm'][1:];simplified=[p[0]];indices=[0];i=0;attempts=[]
while i<len(p)-1:
    accepted=None
    for j in range(len(p)-1,i,-1):
        hit=clear(p[i],p[j]);attempts.append(dict(start=i,end=j,hit=hit))
        if hit is None:accepted=j;break
    assert accepted is not None,(i,len(p))
    simplified.append(p[accepted]);indices.append(accepted);i=accepted
ctx.assert_unchanged();np.savez_compressed(OUT/'path.npz',shifts_mm=np.vstack([np.zeros(3),simplified]),plug_vertices_mm=plug.v,plug_triangles=plug.f)
r=dict(status='PASS',scope='Simplified continuous straight-segment J18 housing path; no attached J18 wires or mating contact qualification',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in [source/'review.json',source/'path.npz',curvefile,HERE/'upper_pack_geometry.py',HERE/'plan_cam_power_plug_access.py']},
    method='Greedy farthest-visible chords; exact swept convex hull and bounded wire-polyline clearance',
    waypoints_mm=np.vstack([np.zeros(3),simplified]).tolist(),source_indices=indices,initial_release_evidence=str((source/'review.json').relative_to(ROOT)),
    nominal_plug_bounds_mm=np.r_[plug.lo,plug.hi].tolist(),deferred_parts=sorted(deferred),retained_upper_wires=list(wires),retained_fixed_wire_solids=14,
    attempts=attempts,continuous_translation='PASS',mating_interface='BLOCKED',attached_J18_wires='NOT_TESTED',complete_sequence='BLOCKED',
    main_changed=False,approved=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    path_sha256=sha(OUT/'path.npz'),script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('POWER_PLUG_SIMPLE_DONE',r['status'],r['waypoints_mm'],len(attempts),r['elapsed_s'],flush=True)
