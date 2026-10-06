"""Remove float-storage degeneracies in an independent J2 copy only.

No source/main changes. Each attempted merge is bounded in micrometres and
must produce a single oriented closed triangle surface with finite volume.
No structural wall or wire-route approval is implied.
"""
from pathlib import Path
import sys,json,hashlib,time,collections
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate_head_cleanup import geometry_record
import bmesh
OUT=HERE/'terminal_threading';CLEAN=OUT/'cleaned';CLEAN.mkdir(exist_ok=True)
MAIN=PROJECT/'mechanical/mori_v1_2.blend';main_hash=hashlib.sha256(MAIN.read_bytes()).hexdigest()
source=OUT/'candidate.blend';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
assert Path(bpy.data.filepath)==source
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
before={n:geometry_record(o) for n,o in physical.items()}

def mesh_check(mesh):
    mesh.calc_loop_triangles()
    v=np.array([tuple(p.co) for p in mesh.vertices]);f=np.array([tuple(t.vertices) for t in mesh.loop_triangles])
    edges=collections.Counter();orientation=collections.Counter();adj=[set() for _ in v]
    for tri in f:
        for a,b in zip(tri,np.roll(tri,-1)):
            key=tuple(sorted((int(a),int(b))));edges[key]+=1;orientation[key]+=1 if a<b else -1
            adj[a].add(int(b));adj[b].add(int(a))
    rem=set(int(x) for x in f.ravel());groups=[]
    while rem:
        stack=[rem.pop()];count=0
        while stack:
            i=stack.pop();count+=1;new=adj[i]&rem;rem-=new;stack+=list(new)
        groups.append(count)
    area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
    solid=manifold.Manifold(manifold.Mesh64(vert_properties=v,tri_verts=f.astype(np.uint64)))
    stats={'vertices':len(v),'triangles':len(f),'non_two_face_edges':sum(c!=2 for c in edges.values()),
           'misoriented_edges':sum(c!=0 for c in orientation.values()),'zero_area_faces':int(np.sum(area<1e-14)),
           'minimum_area_mm2':float(area.min()),'connected_components':groups,'manifold_status':str(solid.status())}
    stats['status']='PASS' if (stats['non_two_face_edges']==stats['misoriented_edges']==stats['zero_area_faces']==0
        and len(groups)==1 and solid.status()==manifold.Error.NoError) else 'FAIL'
    return stats,solid,v,f

rows=[]
for name in ['Yaw_Base','Pitch_Yoke']:
    o=physical[name];original_mesh=o.data;original_stats,original,ov,of=mesh_check(original_mesh)
    attempts=[];accepted=None
    for tolerance in [1e-6,1e-5,5e-5,1e-4]:
        mesh=original_mesh.copy();bm=bmesh.new();bm.from_mesh(mesh)
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=tolerance)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=tolerance)
        # Delete only loose wires/vertices after collapsed zero-area elements.
        loose=[e for e in bm.edges if not e.link_faces]
        if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
        loose=[v for v in bm.verts if not v.link_edges]
        if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.normal_update();bm.to_mesh(mesh);bm.free();mesh.update()
        stats,solid,v,f=mesh_check(mesh)
        stats['merge_distance_mm']=tolerance
        if solid.status()==manifold.Error.NoError:
            # Volume-only booleans can under-report near-coincident surfaces.
            # Also retain absolute volume delta and vertex-to-surface bounds.
            from mathutils.bvhtree import BVHTree
            old_tree=BVHTree.FromPolygons(ov,of.tolist(),all_triangles=True)
            new_tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
            stats['maximum_new_vertex_to_old_surface_mm']=float(max(old_tree.find_nearest(Vector(x))[3] for x in v))
            stats['maximum_old_vertex_to_new_surface_mm']=float(max(new_tree.find_nearest(Vector(x))[3] for x in ov))
            stats['absolute_volume_delta_mm3']=abs(float(solid.volume()-original.volume()))
            stats['surface_difference_scope']='Both vertex sets to opposite triangle surfaces, not an all-surface Hausdorff proof'
            stats['volume_mm3']=float(solid.volume())
            if max(stats['maximum_new_vertex_to_old_surface_mm'],stats['maximum_old_vertex_to_new_surface_mm'])>.001 or stats['absolute_volume_delta_mm3']>.05:
                stats['status']='FAIL'
        attempts.append(stats)
        if stats['status']=='PASS':accepted=(mesh,solid,v,f);break
        bpy.data.meshes.remove(mesh)
    row={'part':name,'original':original_stats,'attempts':attempts,'status':'PASS' if accepted else 'FAIL'}
    if accepted:
        mesh,solid,v,f=accepted;o.data=mesh
        np.savez_compressed(CLEAN/f'{name}.npz',vertices_mm=v,triangles=f)
    rows.append(row);print('J2_STORAGE',name,row['status'],attempts[-1],flush=True)
report={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','parts':rows,
    'source_candidate_sha256':source_hash,'source_blend_sha256':main_hash,
    'source_script_sha256':hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    'scope':'Storage topology cleanup only; mating-clearance blockers retained',
    'main_model_applied':False,'strength':'NOT_TESTED','complete_harness':'BLOCKED'}
if report['status']=='PASS':
    changed=sorted(n for n,o in physical.items() if before[n]!=geometry_record(o));assert changed==['Pitch_Yoke','Yaw_Base']
    report['changed_existing_ids']=changed;report['unchanged_physical_count']=207
    bpy.context.scene['independent_unapproved_study']='J2 topology-cleaned; mated plug clearance BLOCKED, no final harness or print release'
    bpy.ops.wm.save_as_mainfile(filepath=str(CLEAN/'candidate.blend'))
    report['candidate_blend_sha256']=hashlib.sha256((CLEAN/'candidate.blend').read_bytes()).hexdigest()
(CLEAN/'storage_cleanup.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(MAIN.read_bytes()).hexdigest()==main_hash and hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('J2_STORAGE_COMPLETE',report['status'],flush=True)
