"""Normalize only sub-micron storage artifacts in the new neck candidate.

Raw construction meshes and their original blend remain as the reproducible
construction result. A separate cleaned candidate is checked for two-sided
vertex/surface deviation, closed topology, and unchanged other source objects.
"""
import sys,json,hashlib,time,collections
from pathlib import Path
LNS_SCRIPT=Path(__file__).resolve();LNS_A8=LNS_SCRIPT.parent;PROJECT=LNS_A8.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate_head_cleanup import geometry_record
from mathutils.bvhtree import BVHTree
LNS_OUT=LNS_A8/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate'
LNS_CLEAN=LNS_OUT/'cleaned';LNS_CLEAN.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
raw_file=LNS_OUT/'candidate.blend';assert Path(bpy.data.filepath)==raw_file
raw_hash=sha(raw_file);build=json.loads((LNS_OUT/'construction.json').read_text())
assert build['candidate_blend_sha256']==raw_hash
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
assert len(physical)==209
before={n:geometry_record(o) for n,o in physical.items()}
audit=LNS_A8/'repair_threading_storage.py'
code='def mesh_check'+audit.read_text().split('def mesh_check',1)[1].split('\nrows=[]',1)[0]
exec(compile(code,str(audit),'exec'),globals())
def exact_point_triangle_distance(point,vertices,faces):
    """Float64 all-triangle nearest distance, including degenerate edges.

    Blender BVH float arithmetic can overestimate distances near the very
    thin Boolean triangles. Recompute outliers instead of relaxing 1 micron.
    """
    a=vertices[faces[:,0]]-point;b=vertices[faces[:,1]]-point;c=vertices[faces[:,2]]-point
    e=b-a;f=c-a;n=np.cross(e,f);nn=np.einsum('ij,ij->i',n,n)
    signed=np.einsum('ij,ij->i',a,n);valid=nn>1e-28
    q=np.zeros_like(a);q[valid]=n[valid]*(signed[valid]/nn[valid])[:,None]
    inside=valid.copy()
    for x,y in ((a,b),(b,c),(c,a)):
        side=np.einsum('ij,ij->i',np.cross(y-x,q-x),n)
        inside&=side>=-1e-12*nn
    ds=np.full(len(a),np.inf);ds[inside]=signed[inside]**2/nn[inside]
    for x,y in ((a,b),(b,c),(c,a)):
        edge=y-x;den=np.einsum('ij,ij->i',edge,edge);t=np.zeros(len(x))
        ok=den>1e-30;t[ok]=np.clip(-np.einsum('ij,ij->i',x[ok],edge[ok])/den[ok],0,1)
        closest=x+edge*t[:,None];ds=np.minimum(ds,np.einsum('ij,ij->i',closest,closest))
    return float(math.sqrt(max(0.,float(ds.min()))))
def bounded_vertex_distances(points,tree,vertices,faces):
    distances=np.array([float(tree.find_nearest(Vector(p))[3]) for p in points])
    refinements=[]
    for i in np.flatnonzero(distances>.001):
        exact=exact_point_triangle_distance(points[i],vertices,faces)
        refinements.append(dict(vertex=int(i),point_mm=points[i].tolist(),BVH_distance_mm=float(distances[i]),all_triangle_float64_distance_mm=exact))
        distances[i]=exact
    return float(distances.max()),refinements
rows=[]
for n in ('Yaw_Base','Pitch_Yoke'):
    o=physical[n];stats,raw,ov,of=mesh_check(o.data)
    tree_old=BVHTree.FromPolygons(ov,of.tolist(),all_triangles=True)
    cache=np.load(LNS_OUT/(n+'.npz'))
    exact=manifold.Manifold(manifold.Mesh64(cache['vertices_mm'],cache['triangles'].astype(np.uint64)))
    attempts=[];accepted=None
    for tolerance in (0.,.00001,.0001,.0005):
        m=exact.simplify(tolerance)
        for iteration in range(4):
            d=m.to_mesh64();v=np.array(np.array(d.vert_properties[:,:3],dtype=np.float32),dtype=np.float64,order='C',copy=True);f=np.array(d.tri_verts,dtype=np.uint64,order='C',copy=True)
            m=manifold.Manifold(manifold.Mesh64(v,f));kept=[];discarded=[]
            if m.status()!=manifold.Error.NoError:break
            for c in m.decompose():
                cv=np.asarray(c.to_mesh64().vert_properties[:,:3]);center=cv.mean(0)
                _,_,vh=np.linalg.svd(cv-center,full_matrices=False)
                flat=float(np.max(np.abs((cv-center)@vh[-1])))
                ulp=float(np.max(np.spacing(np.abs(cv).astype(np.float32))))
                if abs(c.volume())<1e-7 and flat<=2*ulp:
                    discarded.append(dict(volume_mm3=float(c.volume()),plane_deviation_mm=flat,storage_ULP_mm=ulp))
                else:kept.append(c)
            if len(kept)!=1:break
            m=kept[0].simplify(tolerance);d=m.to_mesh64()
            mesh=bpy.data.meshes.new('A8_LARGER_NECK_'+n)
            mesh.from_pydata(d.vert_properties[:,:3].tolist(),[],d.tri_verts.tolist());mesh.update()
            info,solid,v,f=mesh_check(mesh)
            tree_new=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
            fwd,fwd_refine=bounded_vertex_distances(ov,tree_new,v,f)
            rev,rev_refine=bounded_vertex_distances(v,tree_old,ov,of)
            info.update(tolerance_mm=tolerance,iteration=iteration,numerical_components=discarded,
                        old_vertex_to_new_surface_max_mm=fwd,new_vertex_to_old_surface_max_mm=rev,
                        volume_difference_mm3=abs(float(solid.volume()-raw.volume())),
                        float64_outlier_refinements=dict(old_to_new=fwd_refine,new_to_old=rev_refine))
            if max(fwd,rev)>.001 or info['volume_difference_mm3']>.05:info['status']='FAIL'
            attempts.append(info)
            if info['status']=='PASS':accepted=(mesh,v,f);break
            bpy.data.meshes.remove(mesh)
        if accepted:break
    row=dict(part=n,raw_storage=stats,attempts=attempts,status='PASS' if accepted else 'FAIL');rows.append(row)
    (LNS_CLEAN/(n+'_attempts.json')).write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
    assert accepted,row
    mesh,v,f=accepted;materials=list(o.data.materials);o.data=mesh
    for mat in materials:o.data.materials.append(mat)
    np.savez_compressed(LNS_CLEAN/(n+'.npz'),vertices_mm=v,triangles=f)
    print('LARGER_NECK_STORAGE',n,attempts[-1],flush=True)
changes=sorted(n for n,o in physical.items() if before[n]!=geometry_record(o))
assert not set(changes)-{'Yaw_Base','Pitch_Yoke'}
bpy.context.preferences.filepaths.save_version=0
bpy.context.scene['independent_unapproved_study']='Larger ASSUMED neck contact space, storage cleaned; not approved for main model'
bpy.ops.wm.save_as_mainfile(filepath=str(LNS_CLEAN/'candidate.blend'))
report=dict(status='PASS',scope='Two candidate mesh storage normalizations only; no strength or full assembly claim',
    script_sha256=sha(LNS_SCRIPT),audit_helper_sha256=sha(audit),source_candidate_sha256=raw_hash,
    source_construction_sha256=sha(LNS_OUT/'construction.json'),source_main_sha256=build['source_main_sha256'],
    protected_sources=build['protected_sources'],rows=rows,changed_candidate_parts=changes,
    unchanged_robot_objects=209-len(changes),vertex_surface_comparison_scope='Both vertex sets against opposite surfaces, not full Hausdorff proof',
    output_candidate_sha256=sha(LNS_CLEAN/'candidate.blend'),
    main_applied=False,complete_harness='BLOCKED',strength='NOT_TESTED',manufacturing_release=False)
(LNS_CLEAN/'storage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(raw_file)==raw_hash and all(sha(PROJECT/p)==h for p,h in build['protected_sources'].items())
print('LARGER_NECK_STORAGE_DONE PASS',flush=True)
