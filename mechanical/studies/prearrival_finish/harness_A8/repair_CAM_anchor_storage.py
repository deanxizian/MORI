"""Bounded float-mesh repair in a new independent anchor candidate copy."""
from pathlib import Path
import sys, json, hashlib
SCRIPT=Path(__file__).resolve();A8=SCRIPT.parent
sys.path.insert(0,str(A8.parents[3]/'mechanical/scripts'))
from common import *
from export import topology
from validate_head_cleanup import geometry_record
from mathutils.bvhtree import BVHTree

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=A8/'cam_anchors/candidate_v3';out=source/'cleaned';out.mkdir(exist_ok=True)
main=A8.parents[3]/'mechanical/mori_v1_2.blend';main_hash=sha(main)
assert Path(bpy.data.filepath)==source/'candidate.blend'
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}

def inspect(mesh, matrix):
    mesh.calc_loop_triangles()
    v=np.array([tuple(matrix@p.co) for p in mesh.vertices])
    f=np.array([tuple(t.vertices) for t in mesh.loop_triangles])
    top=topology(v,f.tolist());m=manifold.Manifold(manifold.Mesh64(v,f))
    ok=m.status()==manifold.Error.NoError and all(top[k]==0 for k in
        ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles'])
    return ok,top,m,v,f

o=physical['Pitch_Yoke'];original_mesh=o.data
_,old_top,old,ov,of=inspect(original_mesh,o.matrix_world)
old_tree=BVHTree.FromPolygons(ov,of.tolist(),all_triangles=True)
attempts=[];accepted=False
for tolerance in [1e-6,1e-5,5e-5,1e-4]:
    mesh=original_mesh.copy();bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=tolerance)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=tolerance)
    edges=[e for e in bm.edges if not e.link_faces]
    if edges:bmesh.ops.delete(bm,geom=edges,context='EDGES')
    vertices=[v for v in bm.verts if not v.link_edges]
    if vertices:bmesh.ops.delete(bm,geom=vertices,context='VERTS')
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update();bm.to_mesh(mesh);bm.free();mesh.update()
    ok,top,m,v,f=inspect(mesh,o.matrix_world)
    row={'merge_distance_mm':tolerance,'topology':top,'status':'FAIL'}
    if m.status()==manifold.Error.NoError:
        tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
        a=float(max(tree.find_nearest(Vector(x))[3] for x in ov))
        b=float(max(old_tree.find_nearest(Vector(x))[3] for x in v))
        delta=abs(float(m.volume()-old.volume()))
        row.update(max_old_vertex_to_new_surface_mm=a,max_new_vertex_to_old_surface_mm=b,
                   absolute_volume_delta_mm3=delta)
        ok=ok and max(a,b)<.001 and delta<.05
    attempts.append(row)
    if ok:
        row['status']='PASS';o.data=mesh;accepted=True
        np.savez_compressed(out/'Pitch_Yoke.npz',vertices_mm=v,triangles=f)
        break
    bpy.data.meshes.remove(mesh)
assert accepted,attempts

# The yaw base did not change for this clamp. Restore the already checked raw
# stored J3M mesh instead of re-triangulating its double-precision cache again.
j3m=A8/'assembly_feed_v3/open_mouth/cleaned/candidate.blend'
with bpy.data.libraries.load(str(j3m),link=False) as (data_from,data_to):
    data_to.objects=[PREFIX+'Yaw_Base']
stored=data_to.objects[0]
host=physical['Yaw_Base'];old_base=host.data
host.data=stored.data.copy();bpy.data.objects.remove(stored,do_unlink=True)
ok,base_top,base_m,bv,bf=inspect(host.data,host.matrix_world)
assert ok
np.savez_compressed(out/'Yaw_Base.npz',vertices_mm=bv,triangles=bf)
changed=sorted(n for n,o in physical.items() if geometry_record(o)!=before[n])
assert set(changed)<= {'Pitch_Yoke','Yaw_Base'}
bpy.context.scene['independent_unapproved_study']='A8 CAM yaw-side anchor, raw topology repaired, not main adoption'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'candidate.blend'))
result={'status':'PASS','scope':'Float-storage repair only, new independent copy',
        'script_sha256':sha(SCRIPT),'source_main_sha256':main_hash,
        'source_candidate_sha256':sha(source/'candidate.blend'),
        'source_J3M_sha256':sha(j3m),'candidate_blend_sha256':sha(out/'candidate.blend'),
        'old_yoke_topology':old_top,'yoke_repair_attempts':attempts,'raw_yaw_base_topology':base_top,
        'surface_difference_scope':'Bidirectional vertex-to-triangle distances, not all-surface Hausdorff proof',
        'files':{p.name:sha(p) for p in out.glob('*.npz')},
        'main_applied':False,'manufacturing_release':False}
(out/'repair.json').write_text(json.dumps(result,indent=2)+'\n')
assert sha(main)==main_hash
print('ANCHOR_STORAGE_REPAIR',result['status'],attempts[-1],flush=True)
