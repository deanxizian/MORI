"""Read final .blend and reconcile render/export evidence without modifying it."""
import sys,hashlib,struct,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from pipeline_evidence import render_outputs, EXPECTED_RENDER_VIEWS, DELIVERY_EVIDENCE_FILES, sha
bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for name in ['DOCK','COUPONS','DATUMS','KEEP_OUT']:COLS[name].hide_viewport=False
assembled();h=hashlib.sha256()
for o in sorted(parts(),key=lambda o:o.name):
 h.update(o.name.encode());h.update(np.array(o.matrix_world,dtype=np.float64).tobytes());h.update(np.array([tuple(v.co) for v in o.data.vertices],dtype=np.float32).tobytes());o.data.calc_loop_triangles();h.update(np.array([tuple(t.vertices) for t in o.data.loop_triangles],dtype=np.int32).tobytes())
renders=json.loads((ROOT/'reports/render_manifest.json').read_text());exports=json.loads((ROOT/'reports/export_manifest.json').read_text());manifest=json.loads((ROOT/'reports/build_manifest.json').read_text())
render_files=render_outputs(ROOT,renders,EXPECTED_RENDER_VIEWS,h.hexdigest())
result={'render_files':render_files,'all_render_files_match':render_files['status']=='PASS','render_geometry_sha256':h.hexdigest(),'all_render_hashes_match_final_model':all(v['geometry_sha256']==h.hexdigest() for v in renders),'render_count':len(renders),'all_stl_hashes_match':all(hashlib.sha256((ROOT/v['file']).read_bytes()).hexdigest()==v['sha256'] for v in exports['parts']),'input_hashes_match':all(hashlib.sha256((PROJECT/p).read_bytes()).hexdigest()==value for p,value in manifest['input_sha256'].items()),'foreign_test_object_absent':bpy.data.objects.get('MORI_TEST_FOREIGN_OBJECT_PRESERVATION') is None,'actuators':len([o for o in parts() if o.get('actuator_id')])}
# Hardware may publish a read-only evidence addendum while current geometry is
# rendering. Preserve the real build hash and test its immutable snapshot;
# never relabel the model as having adopted that later hardware selection.
result['input_provenance_valid']=result['input_hashes_match']
result['latest_hardware_addendum_adopted']=False
drift={p:value for p,value in manifest['input_sha256'].items() if hashlib.sha256((PROJECT/p).read_bytes()).hexdigest()!=value}
body_receipt=ROOT/'studies/prearrival_finish/body_split_adoption/contract_receipt.json'
if set(drift)=={'contracts/mechanical_interfaces.json'} and body_receipt.exists():
 receipt=json.loads(body_receipt.read_text());current=json.loads((PROJECT/'contracts/mechanical_interfaces.json').read_text())
 priorpath=PROJECT/receipt['before_snapshot'];prior=json.loads(priorpath.read_text())
 undo=json.loads(json.dumps(current))
 for key in ['revision','mechanical_revision','current_geometry_revision']:undo[key]=prior[key]
 undo['current_authority']['scope']=prior['current_authority']['scope']
 undo['service']['prerequisites']=prior['service']['prerequisites'];undo.pop('body_front_rear_split',None)
 proof=(receipt['status']=='PASS' and receipt['kind']=='POST_BUILD_DOCUMENTATION_ONLY'
        and receipt['before_sha256']==drift['contracts/mechanical_interfaces.json']
        and hashlib.sha256(priorpath.read_bytes()).hexdigest()==receipt['before_sha256']
        and hashlib.sha256((PROJECT/'contracts/mechanical_interfaces.json').read_bytes()).hexdigest()==receipt['after_sha256']
        and hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest()==receipt['source_blend_sha256']
        and undo==prior)
 result['input_provenance_valid']=proof
 result['post_build_documentation_update']={'status':'PASS' if proof else 'FAIL',
  'receipt':str(body_receipt.relative_to(PROJECT)), 'original_build_hash_preserved':True,
  'scope':'Only adopted revision/service descriptions and body-split requirement record added; all construction dimensions and hardware component fields identical.'}
receipt_path=ROOT/'studies/prearrival_finish/hardware_A2_receipt.json'
if set(drift)=={'contracts/components.json'} and receipt_path.exists():
 receipt=json.loads(receipt_path.read_text())
 sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
 source=PROJECT/receipt['source'];handoff=json.loads(source.read_text())
 proof=(receipt['status']=='PASS' and not receipt['main_modified']
        and receipt['built_contract_sha256']==drift['contracts/components.json']
        and sha(PROJECT/receipt['built_contract_snapshot'])==receipt['built_contract_sha256']
        and sha(PROJECT/'contracts/components.json')==receipt['live_contract_sha256']
        and sha(source)==receipt['sha256']
        and sha(PROJECT/handoff['base_handoff'])==handoff['base_handoff_sha256']
        and all(sha(PROJECT/p)==v for p,v in handoff['native_source_manifest'].items())
        and not handoff['native_boards_replaced'])
 result['input_provenance_valid']=proof
 result['hardware_provenance_drift']={'status':'PASS' if proof else 'FAIL','receipt':str(receipt_path.relative_to(PROJECT)),
  'built_contract_sha256':receipt['built_contract_sha256'],'current_contract_sha256':receipt['live_contract_sha256'],
  'scope':'All geometric inputs and native sources match. Only later hardware evidence contract differs; its A2 selections are NOT adopted.',
  'latest_hardware_integration':'BLOCKED'}
structure=json.loads((ROOT/'reports/structure_changes.json').read_text())
actual_modules={o.name.removeprefix(PREFIX):o for o in parts() if o.get('simple_support_module')}
result['structure_report_matches_modules']=set(structure['after'])==set(actual_modules) and structure['support_printed_parts_after']==len(actual_modules) and all(np.max(np.abs(np.array(bounds(o))-np.array(structure['after'][n]['bounds_xyz_mm'])))<.01 for n,o in actual_modules.items())
plan=json.loads((ROOT/'reports/module_assembly.json').read_text());joint_errors=[]
for j in plan['joints']:
 o=bpy.data.objects.get(PREFIX+j['id']+'_Screw')
 if o is None:joint_errors.append(j['id']);continue
 if j.get('axis')=='X':
  bb=bounds(o);yz=[sum(bb[i])/2 for i in [1,2]];sign=j['sign']
  head_x=bb[0][1] if sign>0 else bb[0][0]
  if np.max(np.abs(np.array(yz)-j['center_yz_mm']))>.01 or abs(head_x-j['head_base_mm']-sign*j['head_height_mm'])>.01:joint_errors.append(j['id'])
  continue
 bb=bounds(o);xy=[sum(bb[i])/2 for i in [0,1]]
 head_z=bb[2][0] if j.get('access_direction')=='-Z' else bb[2][1]
 direction=-1 if j.get('access_direction')=='-Z' else 1
 if np.max(np.abs(np.array(xy)-j['xy_mm']))>.01 or abs(head_z-j['head_base_mm']-direction*j.get('head_height_mm',1.6))>.01:joint_errors.append(j['id'])
result['assembly_report_matches_screw_datums']=not joint_errors
result['joint_datum_failures']=joint_errors
metal=json.loads((ROOT/'reports/wheel_metal_export.json').read_text())
result['metal_STEP_units_and_config_match']=metal['source_geometry_sha256']==hashlib.sha256((PROJECT/'config/geometry.json').read_bytes()).hexdigest() and all(row['STEP_reimport_valid_BRep'] and max(abs(a-b) for a,b in zip(row['size_mm'],row['STEP_reimport_size_mm']))<.001 for row in metal['parts'])
from structural_simplification import volume
row=metal['parts'][0];shaft=bpy.data.objects[PREFIX+'Wheel_Axle_R'];bb=bounds(shaft);size=[b-a for a,b in bb];expected=[row['size_mm'][2],row['size_mm'][0],row['size_mm'][1]]
result['metal_STEP_vs_Blender_shaft']={'dimension_error_mm':max(abs(a-b) for a,b in zip(size,expected)),'volume_relative_error':abs(volume(shaft)-row['volume_mm3'])/row['volume_mm3']}
result['metal_STEP_matches_Blender']=result['metal_STEP_vs_Blender_shaft']['dimension_error_mm']<.005 and result['metal_STEP_vs_Blender_shaft']['volume_relative_error']<.01
result['status']='PASS' if all(result[k] for k in ['all_render_files_match','all_render_hashes_match_final_model','all_stl_hashes_match','input_provenance_valid','foreign_test_object_absent','structure_report_matches_modules','assembly_report_matches_screw_datums','metal_STEP_units_and_config_match','metal_STEP_matches_Blender']) and result['actuators']==4 else 'FAIL'
result['stl_topology_failed_ids']=[row['id'] for row in exports['parts'] if row['status']!='PASS']
result['stl_topology_status']='FAIL' if result['stl_topology_failed_ids'] else 'PASS'
result['status_scope']='Input/render/export consistency only; STL topology and manufacturing readiness reported separately.'
result['evidence_sha256']={name:sha(PROJECT/name) for name in DELIVERY_EVIDENCE_FILES}
save_json(ROOT/'reports/delivery_consistency.json',result);print(json.dumps(result))
if result['status']!='PASS':
 raise RuntimeError('Final delivery input/render/export evidence is inconsistent; see delivery_consistency.json')
