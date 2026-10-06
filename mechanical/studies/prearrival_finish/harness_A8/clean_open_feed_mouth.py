# Independent J3M replay copy; only study output directory differs from clean_coupled_feed_candidate.py.
"""Bounded numerical normalization of the independent J3 Blender storage."""
from pathlib import Path
import sys,json,hashlib,time,collections
SCRIPT=Path(__file__).resolve();HERE=SCRIPT.parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate_head_cleanup import geometry_record
from mathutils.bvhtree import BVHTree
OUT=HERE/'assembly_feed_v3/open_mouth';CLEAN=OUT/'cleaned';CLEAN.mkdir(exist_ok=True)
MAIN=PROJECT/'mechanical/mori_v1_2.blend';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
main_hash=sha(MAIN);source=OUT/'candidate.blend';source_hash=sha(source)
assert Path(bpy.data.filepath)==source
load_collections();assembled();bpy.context.view_layer.update()
physical={o.name.removeprefix(PREFIX):o for o in parts() if o.get('group') not in ['dock','coupon']}
assert len(physical)==209
before={n:geometry_record(o) for n,o in physical.items()}
audit_helper=HERE/'repair_threading_storage.py'
code='def mesh_check'+audit_helper.read_text().split('def mesh_check',1)[1].split('\nrows=[]',1)[0]
exec(compile(code,str(audit_helper),'exec'),globals())
rows=[]
for name in ['Yaw_Base','Pitch_Yoke']:
    obj=physical[name];raw_stats,raw_mesh,ov,of=mesh_check(obj.data)
    tree_old=BVHTree.FromPolygons(ov,of.tolist(),all_triangles=True)
    cache=np.load(OUT/f'{name}_candidate.npz')
    exact=manifold.Manifold(manifold.Mesh64(vert_properties=cache['vertices_mm'],tri_verts=cache['triangles'].astype(np.uint64)))
    attempts=[];accepted=None
    for tol in [0.,.00001,.0001,.0005,.001]:
        m=exact.simplify(tol)
        for iteration in range(4):
            data=m.to_mesh64();vv=np.array(data.vert_properties[:,:3],dtype=np.float32).astype(np.float64);ff=np.array(data.tri_verts,dtype=np.uint64)
            m=manifold.Manifold(manifold.Mesh64(vert_properties=vv,tri_verts=ff))
            if m.status()!=manifold.Error.NoError:break
            kept=[];discarded=[]
            for part in m.decompose():
                v=np.array(part.to_mesh64().vert_properties[:,:3]);c=v.mean(0);_,_,vh=np.linalg.svd(v-c,full_matrices=False)
                flat=float(np.abs((v-c)@vh[-1]).max())
                if abs(part.volume())<1e-6 and flat<1e-5:
                    discarded.append({'volume_mm3':float(part.volume()),'plane_distance_mm':flat})
                else:kept.append(part)
            if len(kept)!=1:break
            m=kept[0].simplify(tol);data=m.to_mesh64();mesh=bpy.data.meshes.new('J3_storage_'+name)
            mesh.from_pydata(np.array(data.vert_properties[:,:3]).tolist(),[],np.array(data.tri_verts).tolist());mesh.update()
            stats,solid,v,f=mesh_check(mesh);tree_new=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
            old_dist=np.array([float(tree_new.find_nearest(Vector(p))[3]) for p in ov])
            stats.update(tolerance_mm=tol,iteration=iteration,numerical_planes=discarded,
                maximum_new_vertex_to_old_surface_mm=max(float(tree_old.find_nearest(Vector(p))[3]) for p in v),
                maximum_old_vertex_to_new_surface_mm=float(old_dist.max()),
                volume_delta_mm3=abs(float(solid.volume()-raw_mesh.volume())),
                volume_mm3=float(solid.volume()))
            if max(stats['maximum_new_vertex_to_old_surface_mm'],stats['maximum_old_vertex_to_new_surface_mm'])>.006 or stats['volume_delta_mm3']>.15:stats['status']='FAIL'
            if stats['status']=='FAIL':
                ar=np.linalg.norm(np.cross(ov[of[:,1]]-ov[of[:,0]],ov[of[:,2]]-ov[of[:,0]]),axis=1)/2
                inc=np.zeros(len(ov))
                for column in range(3):np.maximum.at(inc,of[:,column],ar)
                ids=np.argsort(old_dist)[-8:][::-1]
                stats['largest_old_vertex_deviations']=[{'index':int(i),'point_mm':ov[i].tolist(),
                    'distance_mm':float(old_dist[i]),'largest_incident_triangle_area_mm2':float(inc[i])} for i in ids]
            attempts.append(stats)
            if stats['status']=='PASS':accepted=(mesh,v,f);break
            bpy.data.meshes.remove(mesh)
        if accepted:break
    (OUT/f'{name}_storage_attempts.json').write_text(json.dumps({'original':raw_stats,'attempts':attempts},ensure_ascii=False,indent=2)+'\n')
    assert accepted,(name,'See storage_attempts.json')
    mesh,v,f=accepted;mats=list(obj.data.materials);obj.data=mesh
    for mat in mats:obj.data.materials.append(mat)
    np.savez_compressed(CLEAN/f'{name}.npz',vertices_mm=v,triangles=f)
    rows.append({'part':name,'original_storage':raw_stats,'attempts':attempts,'status':'PASS'})
    print('J3_STORAGE',name,attempts[-1],flush=True)
changes=sorted(n for n,o in physical.items() if before[n]!=geometry_record(o))
assert not(set(changes)-{'Yaw_Base','Pitch_Yoke'})
bpy.context.scene['independent_unapproved_study']='J3 coupled loose terminal+wire feed; candidate only, minimum walls and assembly transition pending'
bpy.ops.wm.save_as_mainfile(filepath=str(CLEAN/'candidate.blend'))
report={'status':'PASS','scope':'Raw float32 geometry topology and bounded vertex-to-surface numerical cleanup only',
    'source_blend_sha256':main_hash,'source_candidate_sha256':source_hash,'source_script_sha256':sha(SCRIPT),
    'source_mesh_audit_helper_sha256':sha(audit_helper),'candidate_blend_sha256':sha(CLEAN/'candidate.blend'),
    'rows':rows,'unchanged_other_sources':207,'minimum_wall_and_strength':'NOT_TESTED',
    'complete_harness':'BLOCKED','main_applied':False,'all_surface_deviation_bound':'NOT_TESTED'}
(CLEAN/'storage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash and sha(MAIN)==main_hash
print('J3_STORAGE_COMPLETE',flush=True)
