"""Read the saved sample blend and import its STL files at unit scale."""
from pathlib import Path
import sys,json,hashlib
OUT=Path(__file__).resolve().parent/'fit_coupons';PROJECT=OUT.parents[4]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import bpy,vertices_world,bounds
from export import topology
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());main=PROJECT/'mechanical/mori_v1_2.blend'
assert sha(main)==m['source_blend_sha256']
assert sha(Path(bpy.data.filepath))==m['editable']['sha256']
sc=bpy.data.scenes['MORI_Body_Seam_Trial_M1_51'];bpy.context.window.scene=sc;bpy.context.view_layer.update()
if not sc.get('standalone_file_ready'):
    sc['standalone_file_ready']=True
    for other in list(bpy.data.scenes):
        if other!=sc and len(other.objects)==0:bpy.data.scenes.remove(other)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/m['editable']['file']))
    m['editable']['sha256']=sha(OUT/m['editable']['file'])
    (OUT/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
objects={o.name.removeprefix('MORI_BODYFIT_'):o for o in sc.objects if o.type=='MESH'}
assert set(objects)=={'Front_Male','Rear_Female'}
results=[]
for row in m['parts']:
    o=objects[row['id']];assert tuple(o.location)==(0,0,0) and tuple(o.scale)==(1,1,1)
    path=OUT/row['file'];assert sha(path)==row['sha256'];before=set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=str(path),global_scale=1,use_scene_unit=False,forward_axis='Y',up_axis='Z')
    imported=[x for x in bpy.data.objects if x not in before];assert len(imported)==1
    q=imported[0];bpy.context.view_layer.update();q.data.calc_loop_triangles()
    t=topology(vertices_world(q),[tuple(f.vertices) for f in q.data.loop_triangles])
    assert all(t[k]==0 for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles'])
    assert set(tuple(v) for v in vertices_world(o))==set(tuple(v) for v in vertices_world(q))
    results.append(dict(id=row['id'],status='PASS',topology=t,saved_blend_matches_STL=True,stl_import_scale=1,dimensions_mm=[b-a for a,b in bounds(q)]))
assert sha(main)==m['source_blend_sha256']
(OUT/'readback.json').write_text(json.dumps(dict(status='PASS',source_blend_sha256=m['source_blend_sha256'],editable_sha256=m['editable']['sha256'],parts=results,main_unchanged=True,physical_fit='NOT_TESTED'),ensure_ascii=False,indent=2)+'\n')
print('COUPON_SAVED_BLEND_AND_STL_PASS',flush=True)
