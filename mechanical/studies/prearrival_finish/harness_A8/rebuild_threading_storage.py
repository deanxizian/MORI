"""Normalize the J2 kernel mesh before float32 storage, retaining failures."""
from pathlib import Path
REBUILD_SCRIPT=Path(__file__).resolve()
helper=REBUILD_SCRIPT.with_name('repair_threading_storage.py');__file__=str(helper)
exec(compile(helper.read_text().split('rows=[]')[0],str(helper),'exec'),globals())
__file__=str(REBUILD_SCRIPT)
from mathutils.bvhtree import BVHTree
rows=[]
for name in ['Yaw_Base','Pitch_Yoke']:
    o=physical[name];old_stats,old,ov,of=mesh_check(o.data)
    old_tree=BVHTree.FromPolygons(ov,of.tolist(),all_triangles=True)
    raw=np.load(OUT/f'{name}_candidate.npz')
    reference=manifold.Manifold(manifold.Mesh64(vert_properties=raw['vertices_mm'],tri_verts=raw['triangles'].astype(np.uint64)))
    attempts=[];accepted=None
    for tolerance in [.0005,.001,.003,.005]:
        m=reference.simplify(tolerance)
        for iteration in range(4):
            data=m.to_mesh64();v=np.array(np.asarray(data.vert_properties[:,:3],dtype=np.float32),dtype=np.float64,order='C',copy=True);f=np.array(data.tri_verts,dtype=np.uint64,order='C',copy=True)
            normalized=manifold.Manifold(manifold.Mesh64(vert_properties=v,tri_verts=f))
            if normalized.status()!=manifold.Error.NoError:
                attempts.append({'tolerance_mm':tolerance,'iteration':iteration,'status':'FAIL','manifold_status':str(normalized.status())});break
            # The kernel removes degenerate folded triangles during this
            # reconstruction. Inspect the actual result, not the source index list.
            kept=[];discarded=[]
            for part in normalized.decompose():
                # Float32 normalization can inflate an originally coplanar
                # fragment to ~2e-8 mm3. Require both near-zero volume and a
                # <0.01 micrometre fitted-plane thickness, not volume alone.
                if abs(part.volume())<1e-6:
                    vv=np.asarray(part.to_mesh64().vert_properties[:,:3]);centre=vv.mean(0)
                    _,_,vh=np.linalg.svd(vv-centre,full_matrices=False)
                    flat=float(np.max(abs((vv-centre)@vh[-1])))
                    if flat<1e-5:
                        discarded.append({'volume_mm3':float(part.volume()),'plane_distance_mm':flat,'bounds_mm':list(part.bounding_box())});continue
                kept.append(part)
            if len(kept)!=1:
                attempts.append({'tolerance_mm':tolerance,'iteration':iteration,'status':'FAIL','component_volumes_mm3':[float(p.volume()) for p in kept]});break
            m=kept[0].simplify(tolerance);data=m.to_mesh64()
            mesh=bpy.data.meshes.new('J2_float_storage_check')
            mesh.from_pydata(np.asarray(data.vert_properties[:,:3]).tolist(),[],np.asarray(data.tri_verts).tolist());mesh.update()
            stats,saved,v,f=mesh_check(mesh);stats.update(tolerance_mm=tolerance,iteration=iteration,numerical_planar_fragments=discarded)
            if stats['status']=='PASS':
                new_tree=BVHTree.FromPolygons(v,f.tolist(),all_triangles=True)
                stats['maximum_new_vertex_to_old_surface_mm']=float(max(old_tree.find_nearest(Vector(x))[3] for x in v))
                stats['maximum_old_vertex_to_new_surface_mm']=float(max(new_tree.find_nearest(Vector(x))[3] for x in ov))
                stats['absolute_volume_delta_from_saved_mm3']=abs(float(saved.volume()-old.volume()))
                stats['volume_mm3']=float(saved.volume())
                if max(stats['maximum_new_vertex_to_old_surface_mm'],stats['maximum_old_vertex_to_new_surface_mm'])>.006 or stats['absolute_volume_delta_from_saved_mm3']>.15:
                    stats['status']='FAIL'
            attempts.append(stats)
            if stats['status']=='PASS':accepted=(mesh,saved,v,f);break
            bpy.data.meshes.remove(mesh)
        if accepted:break
    row={'part':name,'original_saved_mesh':old_stats,'attempts':attempts,'status':'PASS' if accepted else 'FAIL'}
    if accepted:
        mesh,saved,v,f=accepted;materials=list(o.data.materials);o.data=mesh
        for material in materials:o.data.materials.append(material)
        np.savez_compressed(CLEAN/f'{name}.npz',vertices_mm=v,triangles=f)
    rows.append(row);print('J2_REBUILT_STORAGE',name,row['status'],attempts[-1],flush=True)
report={'status':'PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL','parts':rows,
    'source_candidate_sha256':source_hash,'source_blend_sha256':main_hash,
    'source_script_sha256':hashlib.sha256(REBUILD_SCRIPT.read_bytes()).hexdigest(),
    'source_helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest(),
    'scope':'Kernel normalization for float32 storage only; mating-clearance blockers retained',
    'main_model_applied':False,'minimum_wall_and_strength':'NOT_TESTED','complete_harness':'BLOCKED'}
if report['status']=='PASS':
    changed=sorted(n for n,o in physical.items() if before[n]!=geometry_record(o));assert changed==['Pitch_Yoke','Yaw_Base']
    report['changed_existing_ids']=changed;report['unchanged_physical_count']=207
    bpy.context.scene['independent_unapproved_study']='J2 normalized storage; mated plug clearance BLOCKED; no manufacturing release'
    bpy.ops.wm.save_as_mainfile(filepath=str(CLEAN/'candidate.blend'))
    report['candidate_blend_sha256']=hashlib.sha256((CLEAN/'candidate.blend').read_bytes()).hexdigest()
(CLEAN/'storage_rebuild.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(MAIN.read_bytes()).hexdigest()==main_hash and hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
print('J2_REBUILT_COMPLETE',report['status'],flush=True)
