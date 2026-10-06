"""Read final .blend and reconcile render/export evidence without modifying it."""
import sys,hashlib,struct,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[name].hide_viewport=False
assembled();h=hashlib.sha256()
for o in sorted(parts(),key=lambda o:o.name):
 h.update(o.name.encode());h.update(np.array(o.matrix_world,dtype=np.float64).tobytes());h.update(np.array([tuple(v.co) for v in o.data.vertices],dtype=np.float32).tobytes());o.data.calc_loop_triangles();h.update(np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.int32).tobytes())
renders=json.loads((ROOT/'reports/render_manifest.json').read_text());exports=json.loads((ROOT/'reports/export_manifest.json').read_text());manifest=json.loads((ROOT/'reports/build_manifest.json').read_text())
result={'render_geometry_sha256':h.hexdigest(),'all_render_hashes_match_final_model':all(v['geometry_sha256']==h.hexdigest() for v in renders),'render_count':len(renders),'all_stl_hashes_match':all(hashlib.sha256((ROOT/v['file']).read_bytes()).hexdigest()==v['sha256'] for v in exports['parts']),'input_hashes_match':all(hashlib.sha256((PROJECT/p).read_bytes()).hexdigest()==value for p,value in manifest['input_sha256'].items()),'foreign_test_object_absent':bpy.data.objects.get('MORI_TEST_FOREIGN_OBJECT_PRESERVATION') is None,'actuators':len([o for o in parts() if o.get('actuator_id')])}
structure=json.loads((ROOT/'reports/structure_changes.json').read_text())
actual_modules={o.name.removeprefix(PREFIX):o for o in parts() if o.get('simple_support_module')}
result['structure_report_matches_modules']=set(structure['after'])==set(actual_modules) and structure['support_printed_parts_after']==len(actual_modules) and all(np.max(np.abs(np.array(bounds(o))-np.array(structure['after'][n]['bounds_xyz_mm'])))<.01 for n,o in actual_modules.items())
plan=json.loads((ROOT/'reports/module_assembly.json').read_text());joint_errors=[]
for j in plan['joints']:
 o=bpy.data.objects.get(PREFIX+j['id']+'_Screw')
 if o is None:joint_errors.append(j['id']);continue
 bb=bounds(o);xy=[sum(bb[i])/2 for i in [0,1]]
 if np.max(np.abs(np.array(xy)-j['xy_mm']))>.01 or abs(bb[2][1]-j['head_base_mm']-1.6)>.01:joint_errors.append(j['id'])
result['assembly_report_matches_screw_datums']=not joint_errors
result['joint_datum_failures']=joint_errors
metal=json.loads((ROOT/'reports/wheel_metal_export.json').read_text())
result['metal_STEP_units_and_config_match']=metal['source_geometry_sha256']==hashlib.sha256((PROJECT/'config/geometry.json').read_bytes()).hexdigest() and all(row['STEP_reimport_valid_BRep'] and max(abs(a-b) for a,b in zip(row['size_mm'],row['STEP_reimport_size_mm']))<.001 for row in metal['parts'])
from structural_simplification import volume
row=metal['parts'][0];shaft=bpy.data.objects[PREFIX+'Wheel_Axle_R'];bb=bounds(shaft);size=[b-a for a,b in bb];expected=[row['size_mm'][2],row['size_mm'][0],row['size_mm'][1]]
result['metal_STEP_vs_Blender_shaft']={'dimension_error_mm':max(abs(a-b) for a,b in zip(size,expected)),'volume_relative_error':abs(volume(shaft)-row['volume_mm3'])/row['volume_mm3']}
result['metal_STEP_matches_Blender']=result['metal_STEP_vs_Blender_shaft']['dimension_error_mm']<.005 and result['metal_STEP_vs_Blender_shaft']['volume_relative_error']<.01
result['status']='PASS' if all(result[k] for k in ['all_render_hashes_match_final_model','all_stl_hashes_match','input_hashes_match','foreign_test_object_absent','structure_report_matches_modules','assembly_report_matches_screw_datums','metal_STEP_units_and_config_match','metal_STEP_matches_Blender']) and result['actuators']==4 else 'FAIL'
save_json(ROOT/'reports/delivery_consistency.json',result);print(json.dumps(result))
if result['status']!='PASS':
 raise RuntimeError('Final delivery input/render/export evidence is inconsistent; see delivery_consistency.json')
