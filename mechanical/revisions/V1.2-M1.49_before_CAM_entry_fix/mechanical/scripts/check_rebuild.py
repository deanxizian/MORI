"""Exercise two rebuilds in an occupied scene; prove foreign-object preservation and deterministic geometry."""
import sys,hashlib,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bpy
import build
from common import *

def signature():
    # Evaluate normally hidden dock/coupon transforms before comparing saved and fresh scenes.
    for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']: COLS[name].hide_viewport=False
    bpy.context.view_layer.update()
    rows={}
    for o in sorted(parts(True),key=lambda o:o.name):
        o.data.calc_loop_triangles(); sha=hashlib.sha256()
        sha.update(np.array([tuple(v.co) for v in o.data.vertices],dtype=np.float32).tobytes());sha.update(np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.int32).tobytes())
        sha.update(np.array(o.matrix_world,dtype=np.float32).tobytes())
        sha.update(np.array([p.use_smooth for p in o.data.polygons],dtype=np.uint8).tobytes())
        sha.update(np.array([e.use_edge_sharp for e in o.data.edges],dtype=np.uint8).tobytes())
        if o.data.has_custom_normals:
            sha.update(np.array([n.vector[:] for n in o.data.corner_normals],dtype=np.float32).round(6).tobytes())
        rows[o.name]=sha.hexdigest()
    return rows
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections();assembled();baseline=signature()
sentinel=bpy.data.objects.new('MORI_TEST_FOREIGN_OBJECT_PRESERVATION',None);bpy.context.scene.collection.objects.link(sentinel);sentinel['test_marker']='not_generator_owned';sentinel.location=(777,888,999)
logs=[]
for i in range(2):
    build.main();assembled();current=signature(); preserved=sentinel.name in bpy.context.scene.objects and tuple(sentinel.location)==(777,888,999)
    logs.append({'iteration':i+1,'part_count':len(current),'same_geometry_and_transforms':current==baseline,'foreign_object_preserved':preserved,'duplicate_name_suffixes':[o.name for o in bpy.context.scene.objects if o.get('mori_owner')==OWNER and o.name[-4:]=='.001']})
bpy.data.objects.remove(sentinel,do_unlink=True)
for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']: COLS[name].hide_viewport=True
pose(0,P['head_joint'].get('default_pitch_deg',0));bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'mori_v1_2.blend'))
save_json(ROOT/'reports/rebuild_check.json',{'status':'PASS' if all(x['same_geometry_and_transforms'] and x['foreign_object_preserved'] and not x['duplicate_name_suffixes'] for x in logs) else 'FAIL','method':'Rebuilt twice in existing populated scene; evaluate hidden dock/coupon collections before geometry/world-transform and display-smoothing/sharp-edge/custom-normal SHA256 comparison; custom normals rounded to 1e-6; unowned sentinel remains; restore normal visibility before saving','runs':logs})
print('REBUILD_CHECK_COMPLETE',flush=True)
