"""Bound a nominal rigid contact's continuous path, not an attached harness.

Each interval uses linear rear-position travel and shortest-quaternion slerp.
The convex hull of the sixteen endpoint vertices is enlarged analytically by
R * (1 - cos(theta / 2)), bounding rotational departure from vertex chords.
All three tested structures remain unapproved independent study geometry.
"""
from pathlib import Path
import itertools, json, math, sys, time

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes'; REST=BASE/'cam_restraints'; OUT=REST/'contact_with_upper_wires'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(HERE))
from upper_pack_geometry import refined

ctx=Context(); started=time.time(); read=lambda p:json.loads(p.read_text())
B=REST/'bench_preassembly_v2';G=REST/'sliding_guide_v4';C=REST/'return_clamp_v3';J=BASE/'cam_side_fans/c6_join'
reports=[B/'review.json',G/'review.json',C/'review.json',J/'join_review.json',BASE/'CAM_PH_RECEIPT.json',REST/'contact_lower_inward/review.json']
inputs=list(reports)+[REST/'contact_continuous/review.json',J/'candidate_curves.npz',HERE/'upper_pack_geometry.py']
for path in reports:
    r=read(path); assert r['status']=='PASS'
    for f,h in {**r.get('sources',{}),**r.get('inputs',{})}.items():assert sha(ROOT/f)==h,f
deferred=set(read(reports[0])['not_yet_installed'])|{'Plug_motion_J5'}
original=ctx.targets; targets={n:t for n,t in original.items() if n not in deferred}
def stored(path):
    inputs.append(path);a=np.load(path)
    return manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
for n,p in [('Pitch_Cradle',C/'Pitch_Cradle_candidate.npz'),('Pitch_Yoke',G/'Pitch_Yoke_candidate.npz'),
            ('connector_band',C/'band.npz'),('connector_head',C/'head.npz'),('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz')]:
    targets[n]=ctx.target(stored(p))
path=REST/'contact_lower_inward/paths.npz';inputs.append(path);paths=np.load(path)
points=paths['lower-0.30_points'];rotations=paths['lower-0.30_rotations'].copy()
assert len(points)==1048 and abs(points[-1,2]-136.5)<1e-8
# A rectangular box is symmetric under 180-degree roll. Select the continuous
# representative instead of inheriting the static screen's axis-sign wrap.
symmetry_fixes=[]
for i in range(1,len(rotations)):
    if np.dot(rotations[i-1,:,0],rotations[i,:,0])<0:
        rotations[i,:,:2]*=-1; symmetry_fixes.append(i)
quats=[]
for r in rotations:
    q=Matrix(r.tolist()).to_quaternion();q.normalize()
    if quats and q.dot(quats[-1])<0:q.negate()
    quats.append(q)
vertices=np.array(list(itertools.product([-1.04,1.04],[-.75,.75],[0.,5.7])))
radius=float(np.linalg.norm(vertices,axis=1).max())
other_names=['P_J9_1','P_J9_2','P_J9_3','P_J18_1','P_J18_2','SPK_reservation_3','SPK_reservation_6']
wiredata=np.load(J/'candidate_curves.npz');upper={}
for name in other_names:
    p=refined(wiredata[name+'_y0'],.01);rad=.4445 if name.startswith('SPK_') else .5842
    upper[name]=dict(p=p,radius=rad,step=float(np.linalg.norm(np.diff(p,axis=0),axis=1).max()),error=.0003)
rows=[];first=None;pair_count=0;minimum=.6;max_error=0.;max_angle=0.
for i in range(len(points)-1):
    dot=abs(float(quats[i].dot(quats[i+1])));angle=2*math.acos(min(1.,max(0.,dot)))
    # Account for float32 quaternion conversion separately from source matrix
    # precision: endpoint vertices below use those same converted matrices.
    r0=np.asarray(quats[i].to_matrix(),float);r1=np.asarray(quats[i+1].to_matrix(),float)
    error=radius*(1-math.cos(angle/2))+2e-5
    hull=manifold.Manifold.hull_points(np.vstack([vertices@r0.T+points[i],vertices@r1.T+points[i+1]]))
    box=np.asarray(hull.bounding_box());interval_min=.6;witness=None;hits=[]
    for name,target in targets.items():
        if not(np.all(box[:3]<=target['hi']+.6+error) and np.all(box[3:]+.6+error>=target['lo'])):continue
        volume=float((hull^target['m']).volume());gap=float(hull.min_gap(target['m'],.6+error)) if abs(volume)<1e-7 else 0.
        bound=gap-error;pair_count+=1
        if bound<interval_min:interval_min=bound;witness=name
        if abs(volume)>1e-6 or bound<.3:hits.append(dict(target=name,overlap_mm3=volume,hull_gap_mm=gap,certified_gap_lower_bound_mm=bound))
    mesh=hull.to_mesh64();v=np.asarray(mesh.vert_properties[:,:3]);f=np.asarray(mesh.tri_verts);tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
    face=v[f[:,0]];norm=np.cross(v[f[:,1]]-face,v[f[:,2]]-face);norm/=np.linalg.norm(norm,axis=1)[:,None]
    assert np.max(np.einsum('ij,ij->i',v.mean(0)-face,norm))<1e-5
    for name,wire in upper.items():
        margin=wire['radius']+.3+wire['step']/2+wire['error']+error+1e-4
        ids=np.flatnonzero(np.all(wire['p']>=box[:3]-margin,axis=1)&np.all(wire['p']<=box[3:]+margin,axis=1))
        for k in ids:
            p=wire['p'][k];inside=np.all(np.einsum('ij,ij->i',p-face,norm)<=0)
            d=0. if inside else float(tree.find_nearest(Vector(p))[3])
            bound=d-wire['radius']-wire['step']/2-wire['error']-error-1e-4
            if bound<.3:
                hits.append(dict(target='UpperWire_'+name,point_mm=p.tolist(),centre_inside_hull=bool(inside),gap_lower_bound_mm=float(bound)))
                break
    rows.append(dict(interval=i,rear_z_mm=float(points[i,2]),gap_lower_bound_mm=interval_min,target=witness,
                     angle_deg=math.degrees(angle),rotation_error_mm=error))
    minimum=min(minimum,interval_min);max_error=max(max_error,error);max_angle=max(max_angle,angle)
    if hits:
        first=dict(interval=i,start_mm=points[i].tolist(),end_mm=points[i+1].tolist(),hits=hits)
        mesh=hull.to_mesh64();np.savez_compressed(OUT/'blocked_hull.npz',vertices_mm=mesh.vert_properties[:,:3],triangles=mesh.tri_verts)
        break
    if i%200==0:print('CONTACT_WITH_UPPER_WIRES_PROGRESS',i,len(points)-1,minimum,flush=True)
ctx.targets=original;ctx.assert_unchanged()
np.savez_compressed(OUT/'path.npz',rear_mm=points,rotations=np.asarray([q.to_matrix() for q in quats],float))
report=dict(status='BLOCKED' if first else 'PASS',scope='Rigid contact path with seven additional fixed upper wire candidates; no installation-order inference',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in set(inputs)},
    interpolation='Linear rear position and shortest quaternion slerp on each recorded interval',
    method='Convex hull of endpoint box vertices plus bounded rotation sagitta',
    interval_count=len(points)-1,checked_intervals=len(rows),native_pair_checks=pair_count,
    minimum_gap_lower_bound_mm=minimum,maximum_rotation_error_mm=max_error,maximum_interval_angle_deg=math.degrees(max_angle),
    terminal_mm=[2.08,1.5,5.7],terminal_evidence='Nominal family box only; actual selected and crimped contact envelope unresolved',
    rear_start_mm=points[0].tolist(),rear_end_mm=points[-1].tolist(),first_failure=first,rows=rows,
    equivalent_box_roll_representatives_corrected=len(symmetry_fixes),Yaw_Reaction_Link_present=True,not_yet_installed=sorted(deferred),
    other_upper_wires=other_names,initial_descent_join='NOT_TESTED',free_wire_shape='NOT_TESTED',peer_CAM_wires='NOT_TESTED',actual_crimped_envelope='BLOCKED',
    full_harness='BLOCKED',main_changed=False,approved=False,C6_main_applied=False,
    output_geometry={p.name:sha(p) for p in OUT.glob('*.npz')},script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('CONTACT_WITH_UPPER_WIRES_DONE',report['status'],minimum,report['elapsed_s'],flush=True)
