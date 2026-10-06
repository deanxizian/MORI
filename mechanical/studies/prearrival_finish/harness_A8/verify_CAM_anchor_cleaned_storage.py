"""Reload the anchor candidate and compare physical geometry with main/J3M.

No official STL export, main scene, hardware source or configuration is saved.
"""
from pathlib import Path
import sys, json, hashlib
SCRIPT = Path(__file__).resolve(); A8 = SCRIPT.parent
PROJECT_DIR = A8.parents[3]
sys.path.insert(0, str(PROJECT_DIR/'mechanical/scripts'))
from common import *
from validate import Solid
from validate_head_cleanup import geometry_record
from export import topology
from mathutils.bvhtree import BVHTree

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
main=PROJECT_DIR/'mechanical/mori_v1_2.blend'
candidate=A8/'cam_anchors/candidate_v3/cleaned'
main_hash=sha(main)
def physical():
    load_collections();assembled();bpy.context.view_layer.update()
    return {o.name.removeprefix(PREFIX):o for o in parts()
            if o.get('group') not in ['dock','coupon']}
assert Path(bpy.data.filepath)==main
original={n:geometry_record(o) for n,o in physical().items()}
bpy.ops.wm.open_mainfile(filepath=str(candidate/'candidate.blend'))
objects=physical();records={n:geometry_record(o) for n,o in objects.items()}
changed=sorted(n for n in original if original[n]!=records[n])
assert changed==['Pitch_Yoke','Yaw_Base']
rows=[]
for n in ['Pitch_Yoke','Yaw_Base']:
    o=objects[n];o.data.calc_loop_triangles()
    vertices=np.array([tuple(o.matrix_world@v.co) for v in o.data.vertices],dtype=float)
    faces=np.array([tuple(t.vertices) for t in o.data.loop_triangles])
    top=topology(vertices,faces.tolist())
    raw=manifold.Manifold(manifold.Mesh64(vertices,faces))
    path=candidate/'Pitch_Yoke.npz' if n=='Pitch_Yoke' else candidate/'Yaw_Base.npz'
    c=np.load(path);reference=manifold.Manifold(manifold.Mesh64(c['vertices_mm'],c['triangles']))
    positive=sum(x.volume()>1e-7 for x in raw.decompose()) if raw.status()==manifold.Error.NoError else 0
    added=max(0.,float((raw-reference).volume()));missing=max(0.,float((reference-raw).volume()))
    ok=(raw.status()==manifold.Error.NoError and positive==1 and added+missing<.005
        and all(top[k]==0 for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles']))
    rows.append({'id':n,'status':'PASS' if ok else 'FAIL','raw_topology':top,
                 'positive_components':positive,'saved_vs_cache_added_mm3':added,
                 'saved_vs_cache_missing_mm3':missing,'cache_sha256':sha(path)})
old=np.load(A8/'assembly_feed_v3/open_mouth/cleaned/Pitch_Yoke.npz')
old_m=manifold.Manifold(manifold.Mesh64(old['vertices_mm'],old['triangles']))
new=Solid(objects['Pitch_Yoke']).m
removed=max(0.,float((old_m-new).volume()))
# Repeat the established numerical-storage bound against the intended union.
# Volume-only differences are unstable near large coincident planes.
added_cache=np.load(candidate.parent/'addition.npz')
intended=old_m+manifold.Manifold(manifold.Mesh64(added_cache['vertices_mm'],added_cache['triangles']))
ref_mesh=intended.to_mesh64();ref_v=np.array(ref_mesh.vert_properties[:,:3]);ref_f=np.array(ref_mesh.tri_verts)
new_mesh=new.to_mesh64();new_v=np.array(new_mesh.vert_properties[:,:3]);new_f=np.array(new_mesh.tri_verts)
ref_tree=BVHTree.FromPolygons(ref_v,ref_f.tolist(),all_triangles=True)
new_tree=BVHTree.FromPolygons(new_v,new_f.tolist(),all_triangles=True)
forward=float(max(ref_tree.find_nearest(Vector(v))[3] for v in new_v))
reverse=float(max(new_tree.find_nearest(Vector(v))[3] for v in ref_v))
volume_delta=abs(float(intended.volume()-new.volume()))
bounds_error=float(np.max(np.abs(np.array(intended.bounding_box())-np.array(new.bounding_box()))))
bounded={'maximum_new_vertex_to_reference_mm':forward,'maximum_reference_vertex_to_new_mm':reverse,
 'absolute_volume_delta_mm3':volume_delta,'bounds_error_mm':bounds_error,
 'vertex_surface_limit_mm':.001,'absolute_volume_limit_mm3':.05,
 'method':'Bidirectional vertex-to-triangle sampling against old J3M plus declared addition; not Hausdorff proof',
 'status':'PASS' if max(forward,reverse,bounds_error)<.001 and volume_delta<.05 else 'FAIL'}
added=max(0.,float((new-old_m).volume()))
ties=[]
for o in bpy.context.scene.objects:
    if not o.name.startswith('A8_CAM_Tie_'):continue
    assert o.get('part_class')=='PLACEHOLDER' and o.get('data_status')=='ASSUMED'
    ties.append(o.name)
result={'status':'PASS' if all(r['status']=='PASS' for r in rows) and bounded['status']=='PASS' else 'FAIL',
        'scope':'Reloaded raw topology and source preservation; no production export',
        'script_sha256':sha(SCRIPT),'source_main_sha256':main_hash,
        'candidate_blend_sha256':sha(candidate/'candidate.blend'),
        'unchanged_physical_parts':len(original)-len(changed),'changed_vs_main':changed,
        'changed_vs_J3M':['Pitch_Yoke'],'near_coincident_boolean_missing_mm3':removed,'intended_union_storage_bound':bounded,
        'added_print_material_mm3':added,'raw_checks':rows,'tie_reference_objects':ties,
        'manufacturing_release':False,'main_applied':False}
(candidate/'storage_verification.json').write_text(json.dumps(result,indent=2)+'\n')
assert sha(main)==main_hash
print('ANCHOR_STORAGE',result['status'],rows,flush=True)
