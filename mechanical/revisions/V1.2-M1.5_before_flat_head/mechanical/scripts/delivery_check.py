"""Read final .blend and reconcile render/export evidence without modifying it."""
import sys,hashlib,struct,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[name].hide_viewport=False
assembled();h=hashlib.sha256()
for o in sorted(parts(),key=lambda o:o.name):
 h.update(o.name.encode());h.update(np.array([tuple(v.co) for v in o.data.vertices],dtype=np.float32).tobytes());o.data.calc_loop_triangles();h.update(np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.int32).tobytes())
renders=json.loads((ROOT/'reports/render_manifest.json').read_text());exports=json.loads((ROOT/'reports/export_manifest.json').read_text());manifest=json.loads((ROOT/'reports/build_manifest.json').read_text())
result={'render_geometry_sha256':h.hexdigest(),'all_render_hashes_match_final_model':all(v['geometry_sha256']==h.hexdigest() for v in renders),'render_count':len(renders),'all_stl_hashes_match':all(hashlib.sha256((ROOT/v['file']).read_bytes()).hexdigest()==v['sha256'] for v in exports['parts']),'input_hashes_match':all(hashlib.sha256((PROJECT/p).read_bytes()).hexdigest()==value for p,value in manifest['input_sha256'].items()),'foreign_test_object_absent':bpy.data.objects.get('MORI_TEST_FOREIGN_OBJECT_PRESERVATION') is None,'actuators':len([o for o in parts() if o.get('actuator_id')])}
result['status']='PASS' if all(result[k] for k in ['all_render_hashes_match_final_model','all_stl_hashes_match','input_hashes_match','foreign_test_object_absent']) and result['actuators']==4 else 'FAIL'
save_json(ROOT/'reports/delivery_consistency.json',result);print(json.dumps(result))
